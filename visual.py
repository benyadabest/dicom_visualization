import os
import pydicom
import numpy as np
import pyvista as pv
from tqdm import tqdm
import logging
import panel as pn
import param
from io import BytesIO
import matplotlib.pyplot as plt
from PIL import Image

pn.extension('vtk')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_t1_series(directory):
    logging.info("Searching for T1 series...")
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith(".dcm"):
                filepath = os.path.join(root, filename)
                try:
                    dicom_data = pydicom.dcmread(filepath, stop_before_pixels=True)
                    series_description = dicom_data.get('SeriesDescription', '').lower()
                    if 't1' in series_description:
                        logging.info(f"T1 series found at: {root}")
                        return root
                except pydicom.errors.InvalidDicomError:
                    logging.warning(f"Invalid DICOM file: {filepath}")
    logging.warning("No T1-weighted series found.")
    return None

def load_dicom_series(directory):
    logging.info(f"Loading DICOM series from {directory}")
    dicom_files = [f for f in os.listdir(directory) if f.lower().endswith('.dcm')]
    dicom_files.sort(key=lambda x: int(pydicom.dcmread(os.path.join(directory, x), stop_before_pixels=True).InstanceNumber))
    
    # Read the first file to get metadata
    ds = pydicom.dcmread(os.path.join(directory, dicom_files[0]))
    img_shape = (int(ds.Rows), int(ds.Columns), len(dicom_files))
    volume = np.zeros(img_shape, dtype=np.float32)
    
    for i, file in tqdm(enumerate(dicom_files), total=len(dicom_files), desc="Loading DICOM files"):
        ds = pydicom.dcmread(os.path.join(directory, file))
        volume[:, :, i] = ds.pixel_array.astype(np.float32)
    
    # Normalize the volume
    volume = (volume - volume.min()) / (volume.max() - volume.min())
    
    pixel_spacing = ds.PixelSpacing
    slice_thickness = ds.SliceThickness
    
    return volume, (pixel_spacing[0], pixel_spacing[1], slice_thickness)

class MRIVisualization(param.Parameterized):
    slice_index = param.Integer(0, bounds=(0, 100))
    view_axis = param.ObjectSelector(default='z', objects=['x', 'y', 'z'])

    def __init__(self, dicom_directory, **params):
        super().__init__(**params)
        self.volume, self.spacing = load_dicom_series(dicom_directory)
        self.param.slice_index.bounds = (0, self.volume.shape[2] - 1)

    @param.depends('slice_index', 'view_axis')
    def view(self):
        fig, ax = plt.subplots(figsize=(8, 8))
        
        if self.view_axis == 'x':
            slice_data = self.volume[self.slice_index, :, :]
        elif self.view_axis == 'y':
            slice_data = self.volume[:, self.slice_index, :]
        else:  # 'z'
            slice_data = self.volume[:, :, self.slice_index]
        
        ax.imshow(slice_data, cmap='gray')
        ax.axis('off')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig)
        
        return pn.pane.PNG(buf, width=400, height=400)

    def panel(self):
        return pn.Column(
            pn.pane.Markdown("# MRI Visualization"),
            pn.Row(
                pn.Column(
                    pn.Param(self.param, widgets={
                        'slice_index': pn.widgets.IntSlider,
                        'view_axis': pn.widgets.RadioBoxGroup
                    }),
                    width=200
                ),
                self.view
            )
        )



def create_mri_visualization(dicom_directory):
    try:
        mri_vis = MRIVisualization(dicom_directory)
        return mri_vis.panel()
    except Exception as e:
        logging.error(f"Failed to create visualization: {str(e)}")
        raise


if __name__ == "__main__":
    dicom_directory = 'dicom/SER00002'
    find_t1_series(dicom_directory)
    panel = create_mri_visualization(dicom_directory)
    panel.show()