from flask import Flask, render_template_string
import panel as pn
import os
from visual import create_mri_visualization

app = Flask(__name__)
pn.extension()

@app.route('/')
def home():
    return """
    <h1>MRI Visualization</h1>
    <a href="/visualize">View MRI Visualization</a>
    """

@app.route('/visualize')
def visualize():
    # Get the absolute path of the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set path for DICOM directory
    dicom_directory = os.path.join(current_dir, 'dicom', 'SER00002')
    
    # Create the visualization panel
    panel = create_mri_visualization(dicom_directory)
    
    # Serve the Panel app
    return panel.server_doc()

if __name__ == '__main__':
    app.run(debug=True, port=5000)