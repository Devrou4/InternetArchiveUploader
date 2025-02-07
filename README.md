# Internet Archive Uploader

A very simple graphical tool for uploading media to the [Internet Archive](https://archive.org/) using the Internet Archive Python library, built with PySide6. This app enables you to easily upload files or collections to the Internet Archive with just a few clicks.

## Features

- Upload files or folders to the Internet Archive.
- Choose the metadata for each upload (e.g., title, description, creator, etc.).
- Supports various types of media: audio, video, images, documents, and more.
- Built using Python, the Internet Archive Python library, and PySide6 for the GUI.
- Monitors upload progress through a virtual console.

## Requirements

The application is packaged as a standalone `.exe` file, so no external dependencies are needed for users. Simply download and run the executable on a Windows machine.

## Installation

1. Download the latest version of the Internet Archive Uploader from the [releases page](#).
   
2. Once downloaded, double-click the `.exe` file to launch the application.

## Usage

1. **Authenticate First**:
   After executing the `.exe` file, **authentication is required** as the first step. The application will prompt you to authenticate with your Internet Archive account. Ensure you have a registered account at [archive.org](https://archive.org/) and log in.

   **Important Security Note**:  
   Your Internet Archive password is **not stored** anywhere by the application. It is only used during the authentication process to obtain your **access** and **private keys** required to perform uploads. This is handled securely through the `internetarchive.configure` method, which is a standard practice for safely managing your API credentials. The password is used solely for the purpose of generating these keys and is never saved or exposed within the application.

2. **Upload Files**:
   - Once authenticated, the application window will appear.
   - Click on the "Select File" or "Select Folder" button to choose the media you want to upload.
   - Fill out the metadata fields (e.g., Title, Creator, Description).
   - Click on "Upload" to start uploading your file or folder to the Internet Archive.

3. **Monitor Progress**:
   Due to limitations in the Internet Archive library, the upload progress is monitored and displayed in a **virtual console** window. This will show the upload progress, including the percentage and file size being uploaded.

## Metadata Explanation

When uploading files to the Internet Archive, you need to provide metadata. This helps describe and categorize the content, making it more discoverable by others. The metadata fields include:

- **`identifier`**: A unique identifier for the item you are uploading. This will be used to track the item in the Internet Archive system. The identifier should be unique to avoid conflicts with other uploads (e.g., "future_of_sustainability_2025").
- **`title`**: The title of the item. This is the name or label given to your uploaded media (e.g., "The Future of Sustainability").
- **`creator`**: The person or entity responsible for creating the content (e.g., "John Doe Productions").
- **`description`**: A brief summary or description of the content being uploaded. This helps users understand what the file is about (e.g., "An insightful documentary about sustainability practices in modern society").
- **`collection`**: The Internet Archive collection to upload your item to. This could be one of the predefined collections such as `"movies"`, `"audio"`, `"texts"`, or others.
- **`subject`**: Keywords or topics related to the content. These are separated by commas to describe the main themes or subjects of the media (e.g., "documentary, sustainability, environment").

Each field helps improve the organization and searchability of your content within the Internet Archive, allowing other users to find it more easily.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
