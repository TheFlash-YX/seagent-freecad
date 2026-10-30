"""Run only inside an authorized NEW FreeCAD/FreeCADCmd test session.

Uses no historical fixtures. Creates known 10x20x30 mm box in a new empty output
folder specified by SEAGENT_SYNTHETIC_OUTPUT. Do not run against business models.
"""
import json
import os
from pathlib import Path
import FreeCAD
import Part

out=Path(os.environ['SEAGENT_SYNTHETIC_OUTPUT']).expanduser()
if not out.is_absolute() or out.exists():raise RuntimeError('Use a NEW absolute synthetic output directory; never overwrite')
out.mkdir(parents=True)
doc=FreeCAD.newDocument('SEAgentSyntheticBox')
obj=doc.addObject('PartDesign::Feature','Box')
obj.Shape=Part.makeBox(10,20,30);doc.recompute()
bb=obj.Shape.BoundBox
actual=[bb.XLength,bb.YLength,bb.ZLength]
assert all(abs(a-b)<1e-6 for a,b in zip(actual,[10,20,30]))
assert abs(obj.Shape.Volume-6000)<1e-6
doc.saveAs(str(out/'synthetic.FCStd'))
Part.export([obj],str(out/'synthetic.step'))
summary={'units':'mm','coordinates':'right-handed XYZ','bbox_mm':actual,'volume_mm3':obj.Shape.Volume,'cwd':os.getcwd(),'gui_python':__import__('sys').version}
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary))
