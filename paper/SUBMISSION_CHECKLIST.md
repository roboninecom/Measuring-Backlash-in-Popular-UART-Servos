# HardwareX Submission Checklist

## Before Submission

### Repository Setup (CRITICAL)
- [ ] Create Zenodo account at https://zenodo.org
- [ ] Upload all design files to Zenodo (NOT GitHub - GitHub is not accepted as primary)
- [ ] Get DOI from Zenodo
- [ ] Update `main_hardwarex.tex` with Zenodo DOI in Specifications Table
- [ ] Ensure repository is **PUBLIC** at time of submission

### Required Files to Upload to Zenodo
- [ ] `/cad/servo_holder.step` and `.stl`
- [ ] `/cad/shaft_coupler.step` and `.stl`
- [ ] `/cad/mounting_plate.step` and `.stl`
- [ ] `/cad/test_lever_100mm.stl`
- [ ] `/cad/teststand/teststand_base.step` and `.stl`
- [ ] `/cad/teststand/puller_mount.stl`
- [ ] `/software/sts3215_control.py`
- [ ] `/software/dual_servo.py`
- [ ] `/software/backlash_test.py`
- [ ] `/software/calibration.py`
- [ ] `/docs/assembly_guide.pdf`
- [ ] `/docs/wiring_diagram.pdf`
- [ ] `LICENSE` files (CERN-OHL-P for hardware, MIT for software)

### Manuscript Preparation
- [ ] Use HardwareX template format ✅ (main_hardwarex.tex created)
- [ ] Specifications Table complete ✅
- [ ] Bill of Materials with costs ✅
- [ ] Build Instructions ✅
- [ ] Operation Instructions ✅
- [ ] Validation and Characterization ✅
- [ ] All required declarations ✅

### Submission Materials
- [ ] Manuscript file (.tex or .docx)
- [ ] Highlights file (separate, 3-5 bullets, max 85 chars each)
- [ ] Graphical abstract (531×1328 pixels minimum, TIFF/EPS/PDF)
- [ ] All figures as separate high-resolution files
- [ ] Declaration of Competing Interests (use Elsevier's declaration tool)

### Optional but Recommended
- [ ] OSHWA Certification at https://certification.oshwa.org
- [ ] If certified, add OSHWA UID to Specifications Table
- [ ] Video demonstration of hardware operation

---

## Highlights (for submission form)

Copy these into the submission system:

```
• Dual-motor system reduces STS3215 servo backlash from 1.30° to 0.09° (14× improvement)
• Open-source 3D-printable design with complete build instructions under $60 USD total cost
• Maintains 80% of combined torque capacity with controlled pretension compensation
• Includes validation test stand, Python control software, and CAD files for replication
• Suitable for educational robotics, research prototyping, and precision motion control
```

---

## Graphical Abstract Requirements

- Minimum size: 531 × 1328 pixels (h × w)
- Format: TIFF, EPS, PDF, or MS Office
- Should summarize: dual-servo configuration → backlash reduction result
- Suggested content:
  - Left: Single servo with backlash visualization (~1.3°)
  - Center: Dual-servo assembly diagram
  - Right: Compensated result (~0.09°)
  - Include key numbers and arrows

---

## Submission Portal

Submit at: https://www.editorialmanager.com/ohx/default.aspx

---

## Key Differences from Original Paper

| Aspect | Original | HardwareX Version |
|--------|----------|-------------------|
| Focus | Research results | Reproducible hardware |
| Structure | Traditional sections | HardwareX template |
| BOM | None | Detailed with costs |
| Build instructions | None | Step-by-step |
| Repository | GitHub only | Zenodo (required) |
| License | CC BY 4.0 | CERN-OHL-P + MIT + CC BY |

---

## Common Rejection Reasons to Avoid

1. ❌ Design files on GitHub instead of approved repository
2. ❌ Missing or incomplete Bill of Materials
3. ❌ No demonstrated scientific application
4. ❌ Insufficient build instructions for replication
5. ❌ Not using HardwareX template
6. ❌ Missing open-source license declaration

---

## Contact

HardwareX Editorial: hardwareX@elsevier.com

