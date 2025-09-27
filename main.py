#!/usr/bin/env python3
"""
Cross-Platform Image to PDF Processor using Flet

This application allows users to:
1. Select 2 images using file picker
2. Enter date and class number  
3. Select community name from dropdown
4. Generate a multi-page PDF with text overlay on each page

Works on Windows, Linux (Wayland/X11), and macOS
"""

import flet as ft
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white
from reportlab.lib.pagesizes import letter
import tempfile
import os
from pathlib import Path
import base64
from datetime import datetime
import yaml

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
        
        # Variables to store images
        self.image_files = [None, None]
        self.image_containers = []
        
        # Processing log
        self.processing_log = []
        
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
            
    def refresh_community_dropdown(self):
        """Refresh the community dropdown options"""
        # Update main process tab dropdown
        self.community_dropdown.options = [
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
                    text="Process",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    content=self.create_process_tab()
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
        
    def create_process_tab(self):
        """Create the main processing tab content"""
        # Image selection section
        image_section = self.create_image_section()
        
        # Two-column layout for inputs and log
        inputs_and_log_row = self.create_two_column_layout()
        
        # Button row
        button_row = ft.Row([
            ft.ElevatedButton(
                text="Process Images to PDF",
                on_click=self.process_images,
                disabled=True,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.GREEN,
                    color=ft.Colors.WHITE,
                    padding=ft.padding.all(15)
                ),
                width=200
            ),
            ft.ElevatedButton(
                text="Reset All",
                on_click=self.reset_all,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.ORANGE,
                    color=ft.Colors.WHITE,
                    padding=ft.padding.all(15)
                ),
                width=120
            )
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
        
        # Store reference to process button
        self.process_btn = button_row.controls[0]
        
        # Status text
        self.status_text = ft.Text(
            "Select 2 images to get started",
            size=14,
            color=ft.Colors.GREY_600,
            text_align=ft.TextAlign.CENTER
        )
        
        return ft.Column([
            image_section,
            ft.Divider(),
            inputs_and_log_row,
            ft.Container(button_row, padding=ft.padding.all(20)),
            ft.Container(self.status_text, padding=ft.padding.all(10))
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
        
    def create_image_section(self):
        """Create the image selection section"""
        # File picker
        self.file_picker = ft.FilePicker(on_result=self.on_file_picker_result)
        self.page.overlay.append(self.file_picker)
        
        # Image containers
        image_row = ft.Row([], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
        
        for i in range(2):
            container = self.create_image_container(i)
            self.image_containers.append(container)
            image_row.controls.append(container)
            
        return ft.Container(
            ft.Column([
                ft.Text("Select Images", size=18, weight=ft.FontWeight.BOLD),
                image_row
            ]),
            padding=ft.padding.all(20)
        )
        
    def create_image_container(self, index):
        """Create an individual image container"""
        placeholder = ft.Column([
            ft.Icon(ft.Icons.IMAGE, size=50, color=ft.Colors.GREY_400),
            ft.Text(f"Image {index + 1}", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("Click to select", size=12, color=ft.Colors.GREY_600)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        container = ft.Container(
            content=placeholder,
            width=250,
            height=200,
            bgcolor=ft.Colors.GREY_100,
            border=ft.border.all(2, ft.Colors.GREY_300),
            border_radius=10,
            padding=ft.padding.all(10),
            on_click=lambda e, idx=index: self.select_image(idx),
            ink=True
        )
        
        return container
        
    def create_two_column_layout(self):
        """Create the two-column layout with inputs and log"""
        # Left column - Input fields
        inputs_column = self.create_input_fields()
        
        # Right column - Processing log
        log_column = self.create_log_section()
        
        # Two-column row
        return ft.Row([
            ft.Container(
                content=inputs_column,
                expand=1,
                padding=ft.padding.all(10)
            ),
            ft.Container(
                content=log_column,
                expand=1,
                padding=ft.padding.all(10)
            )
        ], spacing=20)
        
    def create_input_fields(self):
        """Create the input fields section"""
        # Date input
        self.date_field = ft.TextField(
            label="Date",
            hint_text="e.g., 2024-01-15 or Jan15",
            width=200
        )
        
        # Class number input
        self.class_field = ft.TextField(
            label="Class Number",
            hint_text="e.g., 1, 2, 3...",
            width=150
        )
        
        # Community dropdown (simplified - no management buttons here)
        self.community_dropdown = ft.Dropdown(
            label="Community",
            options=[ft.dropdown.Option(key) for key in sorted(self.community_data.keys())],
            width=250
        )
        
        # Output directory
        self.output_dir_field = ft.TextField(
            label="Output Directory",
            value=str(Path.cwd()),
            width=300,
            read_only=True
        )
        
        output_dir_btn = ft.ElevatedButton(
            text="Browse",
            on_click=self.select_output_dir
        )
        
        # Directory picker
        self.dir_picker = ft.FilePicker(on_result=self.on_dir_picker_result)
        self.page.overlay.append(self.dir_picker)
        
        return ft.Column([
            ft.Text("Enter Details", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([self.date_field, self.class_field], spacing=20),
            ft.Container(self.community_dropdown, padding=ft.padding.only(top=10)),
            ft.Container(
                ft.Text("Output Directory", size=14, weight=ft.FontWeight.BOLD),
                padding=ft.padding.only(top=15, bottom=5)
            ),
            ft.Row([
                self.output_dir_field, 
                output_dir_btn
            ], spacing=10, alignment=ft.MainAxisAlignment.START)
        ])
        
    def create_log_section(self):
        """Create the processing log section"""
        self.log_text = ft.Text(
            value="Processing Log:\n(No files processed yet)",
            size=11,
            color=ft.Colors.GREY_700,
            selectable=True
        )
        
        self.log_container_content = ft.Container(
            content=self.log_text,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=5,
            padding=ft.padding.all(10),
            height=200
        )
        
        clear_log_btn = ft.ElevatedButton(
            text="Clear Log",
            on_click=self.clear_log,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.GREY,
                color=ft.Colors.WHITE
            ),
            width=100
        )
        
        return ft.Column([
            ft.Text("Processing History", size=16, weight=ft.FontWeight.BOLD),
            self.log_container_content,
            ft.Container(
                clear_log_btn,
                alignment=ft.alignment.center,
                padding=ft.padding.only(top=10)
            )
        ])
        
    def select_image(self, index):
        """Handle image selection"""
        self.current_image_index = index
        self.file_picker.pick_files(
            dialog_title=f"Select Image {index + 1}",
            file_type=ft.FilePickerFileType.IMAGE,
            allow_multiple=False
        )
        
    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        """Handle file picker result"""
        if e.files and len(e.files) > 0:
            file = e.files[0]
            self.image_files[self.current_image_index] = file
            self.update_image_preview(self.current_image_index, file)
            self.update_status()
        
    def show_community_dialog(self, title, edit_key=None):
        """Show dialog for adding or editing community"""
        print(f"Opening dialog: {title}")  # Debug print
        
        # Form fields
        name_field = ft.TextField(
            label="Community Name",
            value=edit_key if edit_key else "",
            width=300,
            read_only=bool(edit_key)  # Don't allow changing name when editing
        )
        
        description_field = ft.TextField(
            label="Description",
            value=self.community_data.get(edit_key, "") if edit_key else "",
            width=400,
            multiline=True,
            min_lines=3,
            max_lines=5
        )
        
        def save_community(e):
            print("Save button clicked")  # Debug print
            name = name_field.value.strip()
            description = description_field.value.strip()
            
            if not name:
                self.show_error("Community name is required")
                return
                
            if not description:
                self.show_error("Description is required")
                return
                
            # Check for duplicate name (only when adding)
            if not edit_key and name in self.community_data:
                self.show_error(f"Community '{name}' already exists")
                return
                
            # Save the community
            self.community_data[name] = description
            self.save_communities()
            self.refresh_community_dropdown()
            
            # Set as selected if it's a new community
            if not edit_key:
                self.community_dropdown.value = name
                
            self.page.update()
            self.close_dialog(dialog)
            
        def cancel_action(e):
            print("Cancel button clicked")  # Debug print
            self.close_dialog(dialog)
            
        # Create the dialog content
        content_column = ft.Column([
            name_field,
            description_field
        ], height=200, spacing=10, tight=True)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=content_column,
            actions=[
                ft.TextButton("Cancel", on_click=cancel_action),
                ft.TextButton("Save", on_click=save_community, style=ft.ButtonStyle(color=ft.Colors.BLUE))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        # Make sure to close any existing dialog first
        if hasattr(self.page, 'dialog') and self.page.dialog:
            self.page.dialog.open = False
            
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        print("Dialog should be visible now")  # Debug print
            
    def update_image_preview(self, index, file):
        """Update image preview in container"""
        try:
            with open(file.path, 'rb') as f:
                image_data = f.read()
                
            image_base64 = base64.b64encode(image_data).decode()
            
            preview = ft.Column([
                ft.Image(
                    src_base64=image_base64,
                    width=200,
                    height=150,
                    fit=ft.ImageFit.CONTAIN
                ),
                ft.Text(
                    file.name,
                    size=10,
                    color=ft.Colors.GREY_700,
                    text_align=ft.TextAlign.CENTER,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS
                )
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            self.image_containers[index].content = preview
            self.image_containers[index].bgcolor = ft.Colors.GREEN_50
            self.image_containers[index].border = ft.border.all(2, ft.Colors.GREEN_300)
            
            self.page.update()
            
        except Exception as e:
            self.show_error(f"Could not load image: {str(e)}")
            
    def select_output_dir(self, e):
        """Handle output directory selection"""
        self.dir_picker.get_directory_path(dialog_title="Select Output Directory")
        
    def on_dir_picker_result(self, e: ft.FilePickerResultEvent):
        """Handle directory picker result"""
        if e.path:
            self.output_dir_field.value = e.path
            self.page.update()
            
    def update_status(self):
        """Update status text based on loaded images"""
        loaded_images = sum(1 for img in self.image_files if img is not None)
        
        if loaded_images == 0:
            self.status_text.value = "Select 2 images to get started"
            self.status_text.color = ft.Colors.GREY_600
            self.process_btn.disabled = True
        elif loaded_images == 1:
            self.status_text.value = "1 image selected - need 1 more"
            self.status_text.color = ft.Colors.ORANGE
            self.process_btn.disabled = True
        elif loaded_images == 2:
            self.status_text.value = "2 images selected - ready to process!"
            self.status_text.color = ft.Colors.GREEN
            self.process_btn.disabled = False
            
        self.page.update()
        
    def reset_all(self, e):
        """Reset all fields and images"""
        self.image_files = [None, None]
        
        for i, container in enumerate(self.image_containers):
            placeholder = ft.Column([
                ft.Icon(ft.Icons.IMAGE, size=50, color=ft.Colors.GREY_400),
                ft.Text(f"Image {i + 1}", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("Click to select", size=12, color=ft.Colors.GREY_600)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            container.content = placeholder
            container.bgcolor = ft.Colors.GREY_100
            container.border = ft.border.all(2, ft.Colors.GREY_300)
            
        self.date_field.value = ""
        self.class_field.value = ""
        self.community_dropdown.value = None
        
        self.update_status()
        
    def clear_log(self, e):
        """Clear the processing log"""
        self.processing_log = []
        self.update_log_display()
        
    def add_to_log(self, message):
        """Add a message to the processing log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.processing_log.insert(0, log_entry)
        
        if len(self.processing_log) > 10:
            self.processing_log = self.processing_log[:10]
            
        self.update_log_display()
        
    def update_log_display(self):
        """Update the log display text"""
        if not self.processing_log:
            self.log_text.value = "Processing Log:\n(No files processed yet)"
        else:
            log_content = "Processing Log:\n" + "\n".join(self.processing_log)
            self.log_text.value = log_content
        
        self.log_container_content.update()
        self.page.update()
        
    def validate_inputs(self):
        """Validate user inputs"""
        if not self.date_field.value or not self.date_field.value.strip():
            self.show_error("Please enter a date")
            return False
            
        if not self.class_field.value or not self.class_field.value.strip():
            self.show_error("Please enter a class number")
            return False
            
        if not self.community_dropdown.value:
            self.show_error("Please select a community")
            return False
            
        valid_images = [img for img in self.image_files if img is not None]
        if len(valid_images) < 2:
            self.show_error("Please select 2 images")
            return False
            
        return True
        
    def process_images(self, e):
        """Process images and create PDF"""
        if not self.validate_inputs():
            return
            
        try:
            date = self.date_field.value.strip()
            class_number = self.class_field.value.strip()
            community_name = self.community_dropdown.value
            community_text = self.community_data.get(community_name, f"No data for {community_name}")
            
            output_filename = f"{date}_classreview_{community_name}_{class_number}.pdf"
            output_path = Path(self.output_dir_field.value) / output_filename
            
            self.status_text.value = "Processing..."
            self.status_text.color = ft.Colors.BLUE
            self.page.update()
            
            self.create_pdf(output_path, community_text, date, class_number, community_name)
            
            success_msg = f"✓ PDF created: {output_filename}"
            self.add_to_log(success_msg)
            
            self.status_text.value = f"PDF created: {output_filename}"
            self.status_text.color = ft.Colors.GREEN
            self.page.update()
            
            self.show_success(f"PDF created successfully!\n\nFile saved to:\n{output_path}")
            
        except Exception as e:
            error_msg = f"✗ Failed to create PDF: {str(e)}"
            self.add_to_log(error_msg)
            self.status_text.value = "Error occurred"
            self.status_text.color = ft.Colors.RED
            self.page.update()
            self.show_error(f"Failed to create PDF: {str(e)}")
            
    def create_pdf(self, output_path, community_text, date, class_number, community_name):
        """Create PDF from images"""
        valid_images = [img for img in self.image_files if img is not None]
        
        if not valid_images:
            raise ValueError("No valid images to process")
        
        c = canvas.Canvas(str(output_path), pagesize=letter)
        page_width, page_height = letter
        text_area_height = 100
        available_image_height = page_height - text_area_height
        
        for i, img_file in enumerate(valid_images):
            with Image.open(img_file.path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                img_width, img_height = img.size
                
                width_scale = (page_width - 40) / img_width
                height_scale = available_image_height / img_height
                scale = min(width_scale, height_scale)
                
                final_img_width = img_width * scale
                final_img_height = img_height * scale
                
                x_offset = (page_width - final_img_width) / 2
                y_offset = 0
                
                # Add white background for text area at top
                c.setFillColor(white)
                c.rect(0, page_height - text_area_height, page_width, text_area_height, fill=1, stroke=0)
                
                # Add community text only
                c.setFillColor(black)
                c.setFont("Helvetica", 12)
                
                lines = self.wrap_text(community_text, page_width - 20, c)
                y_pos = page_height - 20
                for line in lines:
                    if line == "":  # Empty line for paragraph breaks
                        y_pos -= 8  # Smaller space for empty lines
                    else:
                        c.drawString(10, y_pos, line)
                        y_pos -= 15  # Normal line spacing
                    
                # Page indicator
                c.setFont("Helvetica", 8)
                c.drawString(page_width - 80, page_height - 15, f"Page {i+1} of {len(valid_images)}")
                
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    img.save(temp_file.name, 'JPEG', quality=95)
                    temp_image_path = temp_file.name
                    
                try:
                    c.drawImage(temp_image_path, x_offset, y_offset, 
                              width=final_img_width, height=final_img_height)
                finally:
                    os.unlink(temp_image_path)
                    
                if i < len(valid_images) - 1:
                    c.showPage()
                    
        c.save()
        
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