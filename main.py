#!/usr/bin/env python3
"""
Enhanced Image to PDF Processor using Flet

This application allows users to:
1. Convert tab: Drag & drop images to create basic PDFs
2. Annotate tab: Add community text to existing PDFs
3. Community Management tab: Manage community data

Works on Windows, Linux (Wayland/X11), and macOS
"""

import flet as ft
from PIL import Image, ExifTags
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import tempfile
import os
from pathlib import Path
import base64
import yaml
import io

class ImageToPDFApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Image to PDF Processor"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window_width = 1000
        self.page.window_height = 700
        self.page.window_resizable = True
        
        # Community data file path
        self.communities_file = Path("communities.yaml")
        
        # Load community data from file or use defaults
        self.community_data = self.load_communities()
        
        # Variables for Convert tab
        self.convert_images = []  # List of image file info
        self.convert_drop_area = None
        self.file_picker_timeout = None
        
        # Variables for Annotate tab
        self.annotate_pdfs = []  # List of PDF files
        self.annotate_drop_area = None
        
        
        # Setup UI
        self.setup_ui()
        
    def load_communities(self):
        """Load community data from YAML file"""
        try:
            if self.communities_file.exists():
                with open(self.communities_file, 'r', encoding='utf-8') as f:
                    loaded_data = yaml.safe_load(f)
                    if loaded_data and isinstance(loaded_data, dict):
                        print(f"Loaded {len(loaded_data)} communities from {self.communities_file}")
                        return loaded_data
                    else:
                        print("YAML file exists but is empty or invalid")
        except Exception as e:
            print(f"Error loading communities file: {e}")
            
        # If file doesn't exist or has issues, start with empty dict
        print(f"Creating new communities file: {self.communities_file}")
        empty_communities = {}
        self.save_communities(empty_communities)
        return empty_communities
        
    def save_communities(self, communities_dict=None):
        """Save community data to YAML file"""
        if communities_dict is None:
            communities_dict = self.community_data
            
        try:
            with open(self.communities_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    communities_dict, 
                    f, 
                    default_flow_style=False, 
                    allow_unicode=True,
                    sort_keys=True
                )
        except Exception as e:
            self.show_error(f"Error saving communities file: {e}")
            
    def setup_ui(self):
        """Setup the main user interface with tabs"""
        # Title
        title = ft.Text(
            "Image to PDF Processor",
            size=24,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER
        )
        
        # Create tabs
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Convert",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    content=self.create_convert_tab()
                ),
                ft.Tab(
                    text="Annotate",
                    icon=ft.Icons.TEXT_FIELDS,
                    content=self.create_annotate_tab()
                ),
                ft.Tab(
                    text="Communities",
                    icon=ft.Icons.SETTINGS,
                    content=self.create_communities_tab()
                )
            ]
        )
        
        # Main layout
        self.page.add(
            ft.Column([
                ft.Container(title, padding=ft.padding.all(20)),
                ft.Container(tabs, expand=True, padding=ft.padding.all(10))
            ])
        )
        
    def create_convert_tab(self):
        """Create the convert tab - drag images to create basic PDFs"""
        # Instructions
        instructions = ft.Text(
            "Click to select 2 images to create a PDF (no community text added)",
            size=16,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.BLUE_GREY_600
        )
        
        # Image selection area
        self.convert_drop_area = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.CLOUD_UPLOAD, size=64, color=ft.Colors.BLUE_300),
                ft.Text("Click to Select Images", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Select up to 2 images at once", size=14, color=ft.Colors.BLUE_600),
                ft.Text("Supports: JPG, PNG, BMP, TIFF, GIF", size=12, color=ft.Colors.GREY_500)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=600,
            height=200,
            bgcolor=ft.Colors.BLUE_50,
            border=ft.border.all(2, ft.Colors.BLUE_200),
            border_radius=10,
            alignment=ft.alignment.center,
            on_click=self.browse_convert_images,
            on_hover=self.on_convert_area_hover
        )
        
        # Image preview area
        self.convert_preview_row = ft.Row([], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
        
        # Initialize the preview row with the drop area
        self.update_convert_preview()
        
        # Convert form
        self.convert_date = ft.TextField(
            label="Date", 
            hint_text="e.g., 2024-01-15", 
            width=200,
            on_change=self.on_convert_date_changed
        )
        self.convert_class = ft.TextField(
            label="Class Number", 
            hint_text="e.g., 1", 
            width=150,
            on_change=self.on_convert_class_changed
        )
        self.convert_community = ft.Dropdown(
            label="Community (optional)",
            options=[ft.dropdown.Option(key) for key in sorted(self.community_data.keys())],
            width=250,
            on_change=self.on_convert_community_changed
        )
        
        convert_form = ft.Row([
            self.convert_date,
            self.convert_class,
            self.convert_community
        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER)
        
        # Output directory - use Documents folder if it exists, otherwise home directory
        documents_path = Path.home() / "Documents"
        if documents_path.exists():
            default_output_dir = str(documents_path)
        else:
            default_output_dir = str(Path.home())
        self.convert_output_dir = ft.TextField(
            label="Output Directory",
            value=default_output_dir,
            width=400,
            read_only=True
        )
        
        convert_output_row = ft.Row([
            self.convert_output_dir,
            ft.ElevatedButton("Browse", on_click=self.browse_convert_output)
        ], spacing=10, alignment=ft.MainAxisAlignment.CENTER)
        
        # Buttons
        convert_buttons = ft.Row([
            ft.ElevatedButton(
                "Convert to PDF",
                on_click=self.convert_images_to_pdf,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE),
                width=150,
                disabled=True
            ),
            ft.ElevatedButton(
                "Clear All",
                on_click=self.clear_convert,
                style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE, color=ft.Colors.WHITE),
                width=100
            )
        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER)
        
        self.convert_btn = convert_buttons.controls[0]
        
        # Status
        self.convert_status = ft.Text(
            "Drop 2 images to get started",
            size=14,
            color=ft.Colors.GREY_600,
            text_align=ft.TextAlign.CENTER
        )
        
        # File picker for convert
        self.convert_file_picker = ft.FilePicker(on_result=self.on_convert_files_picked)
        self.page.overlay.append(self.convert_file_picker)
        
        # Directory picker for convert
        self.convert_dir_picker = ft.FilePicker(on_result=self.on_convert_dir_picked)
        self.page.overlay.append(self.convert_dir_picker)
        
        return ft.Column([
            ft.Container(instructions, padding=ft.padding.all(20)),
            ft.Container(
                content=self.convert_preview_row,
                alignment=ft.alignment.center,
                padding=ft.padding.all(20)
            ),
            ft.Container(
                ft.Column([
                    ft.Text("PDF Details", size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    convert_form,
                    ft.Container(height=10),
                    convert_output_row
                ]),
                padding=ft.padding.all(20),
                bgcolor=ft.Colors.GREY_50,
                border_radius=10
            ),
            ft.Container(height=20),
            convert_buttons,
            ft.Container(self.convert_status, padding=ft.padding.all(10))
        ], scroll=ft.ScrollMode.AUTO)
        
    def create_annotate_tab(self):
        """Create the annotate tab - add community text to existing PDFs"""
        # Instructions
        instructions = ft.Text(
            "Select existing PDFs and add community information to them",
            size=16,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.PURPLE_600
        )
        
        # PDF selection - scrollable with limited height
        self.annotate_pdf_list = ft.Column([], spacing=10, scroll=ft.ScrollMode.AUTO)
        
        pdf_section = ft.Container(
            content=ft.Column([
                ft.Text("Select PDFs to Annotate", size=16, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton(
                    "Browse for PDFs",
                    on_click=self.browse_annotate_pdfs,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE, color=ft.Colors.WHITE),
                    width=150
                ),
                ft.Container(
                    content=self.annotate_pdf_list,
                    height=200,  # Limit height to 200px
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=5,
                    padding=ft.padding.all(10)
                )
            ], spacing=10),
            padding=ft.padding.all(20),
            bgcolor=ft.Colors.PURPLE_50,
            border=ft.border.all(1, ft.Colors.PURPLE_200),
            border_radius=10
        )
        
        # Community selection
        self.annotate_community = ft.Dropdown(
            label="Select Community",
            options=[ft.dropdown.Option(key) for key in sorted(self.community_data.keys())],
            width=300,
            on_change=self.on_annotate_community_changed
        )
        
        # Output directory - use Documents folder if it exists, otherwise home directory
        documents_path = Path.home() / "Documents"
        if documents_path.exists():
            default_output_dir = str(documents_path)
        else:
            default_output_dir = str(Path.home())
        self.annotate_output_dir = ft.TextField(
            label="Output Directory",
            value=default_output_dir,
            width=400,
            read_only=True
        )
        
        annotate_form = ft.Container(
            content=ft.Column([
                ft.Text("Annotation Details", size=16, weight=ft.FontWeight.BOLD),
                self.annotate_community,
                ft.Container(height=10),
                ft.Row([
                    self.annotate_output_dir,
                    ft.ElevatedButton("Browse", on_click=self.browse_annotate_output)
                ], spacing=10)
            ], spacing=10),
            padding=ft.padding.all(20),
            bgcolor=ft.Colors.GREY_50,
            border_radius=10
        )
        
        # Buttons
        annotate_buttons = ft.Row([
            ft.ElevatedButton(
                "Annotate PDFs",
                on_click=self.annotate_pdfs_action,
                style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE, color=ft.Colors.WHITE),
                width=150,
                disabled=True
            ),
            ft.ElevatedButton(
                "Clear Selection",
                on_click=self.clear_annotate,
                style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE, color=ft.Colors.WHITE),
                width=120
            )
        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER)
        
        self.annotate_btn = annotate_buttons.controls[0]
        
        # Status
        self.annotate_status = ft.Text(
            "Select PDFs and community to get started",
            size=14,
            color=ft.Colors.GREY_600,
            text_align=ft.TextAlign.CENTER
        )
        
        # File pickers for annotate
        self.annotate_file_picker = ft.FilePicker(on_result=self.on_annotate_files_picked)
        self.page.overlay.append(self.annotate_file_picker)
        
        self.annotate_dir_picker = ft.FilePicker(on_result=self.on_annotate_dir_picked)
        self.page.overlay.append(self.annotate_dir_picker)
        
        return ft.Column([
            ft.Container(instructions, padding=ft.padding.all(20)),
            pdf_section,
            ft.Container(height=20),
            annotate_form,
            ft.Container(height=20),
            annotate_buttons,
            ft.Container(self.annotate_status, padding=ft.padding.all(10))
        ], scroll=ft.ScrollMode.AUTO)
        
    def create_communities_tab(self):
        """Create the communities management tab content"""
        # Header
        header = ft.Text(
            "Community Management",
            size=20,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER
        )
        
        # Add new community section
        self.new_community_name = ft.TextField(
            label="Community Name",
            hint_text="Enter community name",
            width=250
        )
        
        self.new_community_desc = ft.TextField(
            label="Description",
            hint_text="Enter community description",
            width=400,
            multiline=True,
            min_lines=2,
            max_lines=4
        )
        
        add_button = ft.ElevatedButton(
            text="Add Community",
            on_click=self.add_community_tab,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.GREEN,
                color=ft.Colors.WHITE
            ),
            width=150
        )
        
        add_section = ft.Container(
            content=ft.Column([
                ft.Text("Add New Community", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([self.new_community_name, add_button], spacing=20, alignment=ft.MainAxisAlignment.START),
                self.new_community_desc
            ], spacing=10),
            bgcolor=ft.Colors.GREEN_50,
            border=ft.border.all(1, ft.Colors.GREEN_200),
            border_radius=10,
            padding=ft.padding.all(20)
        )
        
        # Edit section
        self.edit_community_dropdown = ft.Dropdown(
            label="Select Community to Edit",
            options=[ft.dropdown.Option(key) for key in sorted(self.community_data.keys())],
            width=400,
            on_change=self.on_edit_community_selected
        )
        
        self.edit_community_desc = ft.TextField(
            label="Description",
            width=400,
            multiline=True,
            min_lines=2,
            max_lines=4,
            disabled=True
        )
        
        edit_button = ft.ElevatedButton(
            text="Update Community",
            on_click=self.update_community_tab,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE,
                color=ft.Colors.WHITE
            ),
            width=150,
            disabled=True
        )
        
        self.edit_button = edit_button
        
        edit_section = ft.Container(
            content=ft.Column([
                ft.Text("Edit Existing Community", size=16, weight=ft.FontWeight.BOLD),
                self.edit_community_dropdown,
                self.edit_community_desc,
                edit_button
            ], spacing=10),
            bgcolor=ft.Colors.BLUE_50,
            border=ft.border.all(1, ft.Colors.BLUE_200),
            border_radius=10,
            padding=ft.padding.all(20)
        )
        
        # Delete section
        self.delete_community_dropdown = ft.Dropdown(
            label="Select Community to Delete",
            options=[ft.dropdown.Option(key) for key in sorted(self.community_data.keys())],
            width=400
        )
        
        delete_button = ft.ElevatedButton(
            text="Delete Community",
            on_click=self.delete_community_tab,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.RED,
                color=ft.Colors.WHITE
            ),
            width=150
        )
        
        delete_section = ft.Container(
            content=ft.Column([
                ft.Text("Delete Community", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([self.delete_community_dropdown, delete_button], spacing=20, alignment=ft.MainAxisAlignment.START)
            ], spacing=10),
            bgcolor=ft.Colors.RED_50,
            border=ft.border.all(1, ft.Colors.RED_200),
            border_radius=10,
            padding=ft.padding.all(20)
        )
        
        # Status text for communities tab
        self.communities_status = ft.Text(
            f"Total communities: {len(self.community_data)}",
            size=12,
            color=ft.Colors.GREY_600,
            text_align=ft.TextAlign.CENTER
        )
        
        return ft.Column([
            ft.Container(header, padding=ft.padding.all(20)),
            add_section,
            ft.Container(height=20),  # Spacer
            edit_section,
            ft.Container(height=20),  # Spacer
            delete_section,
            ft.Container(self.communities_status, padding=ft.padding.all(20))
        ], scroll=ft.ScrollMode.AUTO)
        
        
    def correct_image_orientation(self, image):
        """Correct image orientation based on EXIF data"""
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            
            if hasattr(image, '_getexif'):
                exif = image._getexif()
                if exif is not None:
                    orientation_value = exif.get(orientation)
                    
                    if orientation_value == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation_value == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation_value == 8:
                        image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, TypeError):
            pass  # No EXIF data or orientation info
            
        return image
        
    # Convert Tab Methods
    def browse_convert_images(self, e):
        """Browse for images in convert tab"""
        print("DEBUG: browse_convert_images called")
        
        # Use tkinter directly for Linux builds as Flet FilePicker has issues
        import platform
        import os
        if platform.system() == "Linux":
            print("DEBUG: Using tkinter fallback for Linux")
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            root.lift()  # Bring to front
            root.attributes('-topmost', True)  # Force on top
            files = filedialog.askopenfilenames(
                title="Select Images",
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.gif")]
            )
            root.destroy()
            if files:
                print(f"DEBUG: Tkinter selected {len(files)} files")
                # Convert to Flet file objects - create a simple object that mimics FilePickerFile
                class MockFilePickerFile:
                    def __init__(self, path):
                        self.path = path
                        self.name = os.path.basename(path)
                
                file_objects = [MockFilePickerFile(f) for f in files]
                self.on_convert_files_picked(type('obj', (object,), {'files': file_objects})())
        else:
            # Use Flet FilePicker for Windows and macOS
            try:
                self.convert_file_picker.pick_files(
                    dialog_title="Select Images",
                    file_type=ft.FilePickerFileType.IMAGE,
                    allow_multiple=True
                )
                print("DEBUG: Flet pick_files called successfully")
            except Exception as ex:
                print(f"DEBUG: Error calling pick_files: {ex}")
        
    def on_convert_files_picked(self, e: ft.FilePickerResultEvent):
        """Handle file picker result for convert tab"""
        if e.files:
            # Take only first 2 files
            self.convert_images = e.files[:2]
            self.update_convert_preview()
            self.update_convert_status()
            
    def on_convert_area_hover(self, e):
        """Handle hover effect on convert area"""
        if e.data == "true":  # Mouse enter
            self.convert_drop_area.bgcolor = ft.Colors.BLUE_100
            self.convert_drop_area.border = ft.border.all(3, ft.Colors.BLUE_400)
        else:  # Mouse leave
            self.convert_drop_area.bgcolor = ft.Colors.BLUE_50
            self.convert_drop_area.border = ft.border.all(2, ft.Colors.BLUE_200)
        self.page.update()
            
    def update_convert_preview(self):
        """Update the preview of selected images"""
        self.convert_preview_row.controls.clear()
        
        if self.convert_images:
            # Show image previews plus "Add More" button
            for i, file in enumerate(self.convert_images):
                try:
                    with open(file.path, 'rb') as f:
                        image_data = f.read()
                    image_base64 = base64.b64encode(image_data).decode()
                    
                    # Create preview with reorder buttons
                    preview_container = ft.Container(
                        content=ft.Column([
                            ft.Text(f"Page {i+1}", size=12, weight=ft.FontWeight.BOLD),
                            ft.Image(
                                src_base64=image_base64,
                                width=150,
                                height=150,
                                fit=ft.ImageFit.CONTAIN
                            ),
                            ft.Text(file.name, size=10, max_lines=2, text_align=ft.TextAlign.CENTER),
                            ft.Row([
                                ft.IconButton(
                                    ft.Icons.ARROW_BACK,
                                    tooltip="Move Left",
                                    on_click=lambda e, idx=i: self.move_image_left(idx),
                                    disabled=i == 0
                                ),
                                ft.IconButton(
                                    ft.Icons.ARROW_FORWARD,
                                    tooltip="Move Right", 
                                    on_click=lambda e, idx=i: self.move_image_right(idx),
                                    disabled=i == len(self.convert_images) - 1
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE,
                                    tooltip="Remove",
                                    on_click=lambda e, idx=i: self.remove_convert_image(idx)
                                )
                            ], alignment=ft.MainAxisAlignment.CENTER)
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=ft.Colors.GREEN_50,
                        border=ft.border.all(1, ft.Colors.GREEN_300),
                        border_radius=10,
                        padding=ft.padding.all(10),
                        width=200
                    )
                    
                    self.convert_preview_row.controls.append(preview_container)
                    
                except Exception as e:
                    print(f"Error creating preview for {file.name}: {e}")
            
            # Add "Add More" button inline with images
            add_more_button = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE, size=32, color=ft.Colors.BLUE_300),
                    ft.Text("Add More", size=14, weight=ft.FontWeight.BOLD),
                    ft.Text("Click to select", size=10, color=ft.Colors.GREY_600)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=200,
                height=150,
                bgcolor=ft.Colors.BLUE_50,
                border=ft.border.all(2, ft.Colors.BLUE_200),
                border_radius=10,
                alignment=ft.alignment.center,
                on_click=self.browse_convert_images,
                on_hover=self.on_convert_area_hover
            )
            self.convert_preview_row.controls.append(add_more_button)
            
        else:
            # Show full-size drop area when no images selected
            self.convert_drop_area.width = 600
            self.convert_drop_area.height = 200
            self.convert_drop_area.content = ft.Column([
                ft.Icon(ft.Icons.CLOUD_UPLOAD, size=64, color=ft.Colors.BLUE_300),
                ft.Text("Click to Select Images", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Select up to 2 images at once", size=14, color=ft.Colors.BLUE_600),
                ft.Text("Supports: JPG, PNG, BMP, TIFF, GIF", size=12, color=ft.Colors.GREY_500)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            self.convert_preview_row.controls.append(self.convert_drop_area)
                
        self.page.update()
        
    def move_image_left(self, index):
        """Move image to the left (lower page number)"""
        if index > 0:
            self.convert_images[index], self.convert_images[index-1] = self.convert_images[index-1], self.convert_images[index]
            self.update_convert_preview()
            
    def move_image_right(self, index):
        """Move image to the right (higher page number)"""
        if index < len(self.convert_images) - 1:
            self.convert_images[index], self.convert_images[index+1] = self.convert_images[index+1], self.convert_images[index]
            self.update_convert_preview()
            
    def remove_convert_image(self, index):
        """Remove image from convert list"""
        self.convert_images.pop(index)
        self.update_convert_preview()
        self.update_convert_status()
        
    def update_convert_status(self):
        """Update status for convert tab"""
        count = len(self.convert_images)
        has_date = bool(self.convert_date.value and self.convert_date.value.strip())
        has_class = bool(self.convert_class.value and self.convert_class.value.strip())
        
        if count == 0:
            self.convert_status.value = "Drop 2 images to get started"
            self.convert_status.color = ft.Colors.GREY_600
            self.convert_btn.disabled = True
        elif count == 1:
            self.convert_status.value = "1 image selected - add 1 more"
            self.convert_status.color = ft.Colors.ORANGE
            self.convert_btn.disabled = True
        elif not has_date or not has_class:
            self.convert_status.value = f"{count} images selected - enter date and class number"
            self.convert_status.color = ft.Colors.ORANGE
            self.convert_btn.disabled = True
        else:
            self.convert_status.value = f"{count} images selected - ready to convert!"
            self.convert_status.color = ft.Colors.GREEN
            self.convert_btn.disabled = False
            
        self.page.update()
        
    def on_convert_community_changed(self, e):
        """Handle community dropdown change in convert tab"""
        self.update_convert_status()
        
    def on_convert_date_changed(self, e):
        """Handle date field change in convert tab"""
        self.update_convert_status()
        
    def on_convert_class_changed(self, e):
        """Handle class field change in convert tab"""
        self.update_convert_status()
        
    def browse_convert_output(self, e):
        """Browse for output directory in convert tab"""
        self.convert_dir_picker.get_directory_path()
        
    def on_convert_dir_picked(self, e: ft.FilePickerResultEvent):
        """Handle directory picker for convert tab"""
        if e.path:
            self.convert_output_dir.value = e.path
            self.page.update()
            
    def convert_images_to_pdf(self, e):
        """Convert images to PDF"""
        print("Convert button clicked!")  # Debug
        
        if not self.convert_images:
            self.show_error("Please select images first")
            return
            
        if not self.convert_date.value or not self.convert_date.value.strip():
            self.show_error("Please enter a date")
            return
            
        if not self.convert_class.value or not self.convert_class.value.strip():
            self.show_error("Please enter a class number")
            return
            
        try:
            date = self.convert_date.value.strip()
            class_number = self.convert_class.value.strip()
            community_name = self.convert_community.value or "unknown"
            
            output_filename = f"{date}_classreview_{community_name}_{class_number}.pdf"
            output_path = Path(self.convert_output_dir.value) / output_filename
            
            self.convert_status.value = "Converting..."
            self.convert_status.color = ft.Colors.BLUE
            self.page.update()
            
            self.create_basic_pdf(output_path)
            
            
            self.convert_status.value = f"PDF created: {output_filename}"
            self.convert_status.color = ft.Colors.GREEN
            
            self.show_success(f"PDF created successfully!\n\nFile saved to:\n{output_path}")
            
        except Exception as e:
            self.convert_status.value = "Error occurred"
            self.convert_status.color = ft.Colors.RED
            self.show_error(f"Failed to create PDF: {str(e)}")
            
        self.page.update()
        
    def create_basic_pdf(self, output_path):
        """Create basic PDF from images without community text"""
        c = canvas.Canvas(str(output_path), pagesize=letter)
        page_width, page_height = letter
        
        for i, img_file in enumerate(self.convert_images):
            with Image.open(img_file.path) as img:
                # Correct orientation
                img = self.correct_image_orientation(img)
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                img_width, img_height = img.size
                
                # Calculate scaling to fit page while maintaining aspect ratio
                width_scale = page_width / img_width
                height_scale = page_height / img_height
                scale = min(width_scale, height_scale)
                
                final_img_width = img_width * scale
                final_img_height = img_height * scale
                
                # Center the image
                x_offset = (page_width - final_img_width) / 2
                y_offset = (page_height - final_img_height) / 2
                
                # Save image to temporary file
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    img.save(temp_file.name, 'JPEG', quality=95)
                    temp_image_path = temp_file.name
                    
                try:
                    c.drawImage(temp_image_path, x_offset, y_offset, 
                              width=final_img_width, height=final_img_height)
                finally:
                    os.unlink(temp_image_path)
                    
                if i < len(self.convert_images) - 1:
                    c.showPage()
                    
        c.save()
        
    def clear_convert(self, e):
        """Clear all convert tab data"""
        self.convert_images = []
        self.convert_preview_row.controls.clear()
        self.convert_date.value = ""
        self.convert_class.value = ""
        self.convert_community.value = None
        self.update_convert_preview()  # This will reset the drop area to full size
        self.update_convert_status()
        
    # Annotate Tab Methods
    def browse_annotate_pdfs(self, e):
        """Browse for PDFs to annotate"""
        print("DEBUG: browse_annotate_pdfs called")
        try:
            self.annotate_file_picker.pick_files(
                dialog_title="Select PDFs to Annotate",
                allowed_extensions=["pdf"],
                allow_multiple=True
            )
            print("DEBUG: pick_files called successfully")
        except Exception as ex:
            print(f"DEBUG: Error calling pick_files: {ex}")
            # Fallback: try to open a simple file dialog
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            files = filedialog.askopenfilenames(
                title="Select PDFs to Annotate",
                filetypes=[("PDF files", "*.pdf")]
            )
            root.destroy()
            if files:
                print(f"DEBUG: Tkinter selected {len(files)} PDF files")
                # Convert to Flet file objects - create a simple object that mimics FilePickerFile
                import os
                class MockFilePickerFile:
                    def __init__(self, path):
                        self.path = path
                        self.name = os.path.basename(path)
                
                file_objects = [MockFilePickerFile(f) for f in files]
                self.on_annotate_files_picked(type('obj', (object,), {'files': file_objects})())
        
    def on_annotate_files_picked(self, e: ft.FilePickerResultEvent):
        """Handle PDF file picker result"""
        if e.files:
            self.annotate_pdfs = e.files
            self.update_annotate_list()
            self.update_annotate_status()
            
    def update_annotate_list(self):
        """Update the list of PDFs to annotate"""
        self.annotate_pdf_list.controls.clear()
        
        for i, file in enumerate(self.annotate_pdfs):
            pdf_item = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PICTURE_AS_PDF, color=ft.Colors.RED),
                    ft.Text(file.name, expand=True),
                    ft.IconButton(
                        ft.Icons.DELETE,
                        tooltip="Remove",
                        on_click=lambda e, idx=i: self.remove_annotate_pdf(idx)
                    )
                ]),
                bgcolor=ft.Colors.GREY_50,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                padding=ft.padding.all(10)
            )
            self.annotate_pdf_list.controls.append(pdf_item)
            
        self.page.update()
        
    def remove_annotate_pdf(self, index):
        """Remove PDF from annotate list"""
        self.annotate_pdfs.pop(index)
        self.update_annotate_list()
        self.update_annotate_status()
        
    def update_annotate_status(self):
        """Update status for annotate tab"""
        pdf_count = len(self.annotate_pdfs)
        has_community = bool(self.annotate_community.value)
        
        if pdf_count == 0:
            self.annotate_status.value = "Select PDFs and community to get started"
            self.annotate_status.color = ft.Colors.GREY_600
            self.annotate_btn.disabled = True
        elif not has_community:
            self.annotate_status.value = f"{pdf_count} PDFs selected - choose community"
            self.annotate_status.color = ft.Colors.ORANGE
            self.annotate_btn.disabled = True
        else:
            self.annotate_status.value = f"{pdf_count} PDFs ready to annotate"
            self.annotate_status.color = ft.Colors.GREEN
            self.annotate_btn.disabled = False
            
        self.page.update()
        
    def on_annotate_community_changed(self, e):
        """Handle community dropdown change in annotate tab"""
        self.update_annotate_status()
        
    def browse_annotate_output(self, e):
        """Browse for output directory in annotate tab"""
        self.annotate_dir_picker.get_directory_path()
        
    def on_annotate_dir_picked(self, e: ft.FilePickerResultEvent):
        """Handle directory picker for annotate tab"""
        if e.path:
            self.annotate_output_dir.value = e.path
            self.page.update()
            
    def annotate_pdfs_action(self, e):
        """Add community information to existing PDFs"""
        print("Annotate button clicked!")  # Debug
        
        if not self.annotate_pdfs:
            self.show_error("Please select PDFs first")
            return
            
        if not self.annotate_community.value:
            self.show_error("Please select a community")
            return
            
        try:
            community_name = self.annotate_community.value
            community_text = self.community_data.get(community_name, f"No data for {community_name}")
            
            self.annotate_status.value = "Annotating PDFs..."
            self.annotate_status.color = ft.Colors.BLUE
            self.page.update()
            
            success_count = 0
            for pdf_file in self.annotate_pdfs:
                try:
                    # Keep original filename
                    output_filename = pdf_file.name
                    output_path = Path(self.annotate_output_dir.value) / output_filename
                    
                    # Add community text to PDF
                    self.add_text_to_pdf(pdf_file.path, output_path, community_text)
                    success_count += 1
                    
                    
                except Exception as e:
                    print(f"Error annotating {pdf_file.name}: {e}")
                    
            self.annotate_status.value = f"Annotated {success_count}/{len(self.annotate_pdfs)} PDFs"
            self.annotate_status.color = ft.Colors.GREEN
            
            self.show_success(f"Successfully annotated {success_count} PDFs!\n\nFiles saved to:\n{self.annotate_output_dir.value}")
            
        except Exception as e:
            self.annotate_status.value = "Error occurred"
            self.annotate_status.color = ft.Colors.RED
            self.show_error(f"Failed to annotate PDFs: {str(e)}")
            
        self.page.update()
        
    def add_text_to_pdf(self, input_pdf_path, output_pdf_path, community_text):
        """Add community text overlay to existing PDF"""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from PyPDF2 import PdfReader, PdfWriter
        import io
        
        # Read the existing PDF
        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()
        
        page_width, page_height = letter
        text_area_height = 100
        
        for page_num, page in enumerate(reader.pages):
            # Create overlay with text
            packet = io.BytesIO()
            overlay_canvas = canvas.Canvas(packet, pagesize=letter)
            
            # Add white background for text area at top
            overlay_canvas.setFillColor(white)
            overlay_canvas.rect(0, page_height - text_area_height, page_width, text_area_height, fill=1, stroke=0)
            
            # Add community text
            overlay_canvas.setFillColor(black)
            overlay_canvas.setFont("Helvetica", 12)
            
            lines = self.wrap_text(community_text, page_width - 20, overlay_canvas)
            y_pos = page_height - 20
            for line in lines:
                if line == "":  # Empty line for paragraph breaks
                    y_pos -= 8
                else:
                    overlay_canvas.drawString(10, y_pos, line)
                    y_pos -= 15
                    
            # Page indicator
            overlay_canvas.setFont("Helvetica", 8)
            overlay_canvas.drawString(page_width - 80, page_height - 15, f"Page {page_num+1} of {len(reader.pages)}")
            
            overlay_canvas.save()
            
            # Move to the beginning of the StringIO buffer
            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            
            # Merge the overlay with the existing page
            page.merge_page(overlay_pdf.pages[0])
            writer.add_page(page)
            
        # Write the result
        with open(output_pdf_path, 'wb') as output_file:
            writer.write(output_file)
            
    def clear_annotate(self, e):
        """Clear all annotate tab data"""
        self.annotate_pdfs = []
        self.annotate_pdf_list.controls.clear()
        self.annotate_community.value = None
        self.update_annotate_status()
        
    # Community Management Methods
    def refresh_community_dropdown(self):
        """Refresh all community dropdown options"""
        # Update convert tab dropdown
        self.convert_community.options = [
            ft.dropdown.Option(key) for key in sorted(self.community_data.keys())
        ]
        
        # Update annotate tab dropdown
        self.annotate_community.options = [
            ft.dropdown.Option(key) for key in sorted(self.community_data.keys())
        ]
        
        # Update communities tab dropdowns if they exist
        if hasattr(self, 'edit_community_dropdown'):
            self.edit_community_dropdown.options = [
                ft.dropdown.Option(key) for key in sorted(self.community_data.keys())
            ]
            
        if hasattr(self, 'delete_community_dropdown'):
            self.delete_community_dropdown.options = [
                ft.dropdown.Option(key) for key in sorted(self.community_data.keys())
            ]
            
        # Update status
        if hasattr(self, 'communities_status'):
            self.communities_status.value = f"Total communities: {len(self.community_data)}"
            
        self.page.update()
        
    def add_community_tab(self, e):
        """Add community from the communities tab"""
        name = self.new_community_name.value.strip()
        description = self.new_community_desc.value.strip()
        
        if not name:
            self.show_communities_status("Error: Community name is required", ft.Colors.RED)
            return
            
        if not description:
            self.show_communities_status("Error: Description is required", ft.Colors.RED)
            return
            
        if name in self.community_data:
            self.show_communities_status(f"Error: Community '{name}' already exists", ft.Colors.RED)
            return
            
        # Add the community
        self.community_data[name] = description
        self.save_communities()
        self.refresh_community_dropdown()
        
        # Clear the form
        self.new_community_name.value = ""
        self.new_community_desc.value = ""
        
        self.show_communities_status(f"Added community '{name}' successfully", ft.Colors.GREEN)
        
        
    def on_edit_community_selected(self, e):
        """Handle community selection for editing"""
        if e.control.value:
            selected_key = e.control.value
            self.edit_community_desc.value = self.community_data.get(selected_key, "")
            self.edit_community_desc.disabled = False
            self.edit_button.disabled = False
            self.page.update()
            
    def update_community_tab(self, e):
        """Update community from the communities tab"""
        selected_key = self.edit_community_dropdown.value
        new_description = self.edit_community_desc.value.strip()
        
        if not selected_key:
            self.show_communities_status("Error: Please select a community to edit", ft.Colors.RED)
            return
            
        if not new_description:
            self.show_communities_status("Error: Description is required", ft.Colors.RED)
            return
            
        # Update the community
        self.community_data[selected_key] = new_description
        self.save_communities()
        self.refresh_community_dropdown()
        
        self.show_communities_status(f"Updated community '{selected_key}' successfully", ft.Colors.GREEN)
        
    def delete_community_tab(self, e):
        """Delete community from the communities tab"""
        selected_key = self.delete_community_dropdown.value
        
        if not selected_key:
            self.show_communities_status("Error: Please select a community to delete", ft.Colors.RED)
            return
            
        # Delete the community
        del self.community_data[selected_key]
        self.save_communities()
        self.refresh_community_dropdown()
        
        # Clear the dropdown
        self.delete_community_dropdown.value = None
        
        self.show_communities_status(f"Deleted community '{selected_key}' successfully", ft.Colors.GREEN)
        
    def show_communities_status(self, message, color):
        """Show status message in communities tab"""
        self.communities_status.value = message
        self.communities_status.color = color
        self.page.update()
        
    # Utility Methods
    def wrap_text(self, text, max_width, canvas_obj):
        """Wrap text to fit within specified width, honoring line breaks"""
        # First split by actual line breaks
        paragraphs = text.split('\n')
        all_lines = []
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                # Empty line - add some spacing
                all_lines.append("")
                continue
                
            # Now wrap each paragraph to fit the width
            words = paragraph.split()
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                text_width = canvas_obj.stringWidth(test_line, "Helvetica", 12)
                
                if text_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        all_lines.append(current_line)
                    current_line = word
                    
            if current_line:
                all_lines.append(current_line)
                
        return all_lines
        
    def show_error(self, message):
        """Show error dialog"""
        dialog = ft.AlertDialog(
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_dialog(dialog))]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        
    def show_success(self, message):
        """Show success dialog"""
        dialog = ft.AlertDialog(
            title=ft.Text("Success"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_dialog(dialog))]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        
    def close_dialog(self, dialog):
        """Close dialog"""
        dialog.open = False
        self.page.update()


def main(page: ft.Page):
    app = ImageToPDFApp(page)


if __name__ == "__main__":
    ft.app(target=main)