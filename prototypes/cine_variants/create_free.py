"""Create Cine free; run this file in Cinema 4D Script Manager."""
from pathlib import Path
import runpy
import c4d


if __name__ == '__main__':
    builder = runpy.run_path(str(Path(__file__).with_name('builder.py')))
    document = c4d.documents.GetActiveDocument()
    root, _, _ = builder['build'](document, mode=2)
    document.SetActiveObject(root)
    c4d.EventAdd()
