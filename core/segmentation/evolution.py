# This Python file uses the following encoding: utf-8

import numpy as np
import SimpleITK as sitk
from PySide6.QtWidgets import QStyle
from scipy import ndimage as ndi
from PySide6.QtCore import QThread, Signal, QObject, Slot
import vtk
from vtk.util import numpy_support
from PySide6.QtCore import Qt
from scipy.ndimage import median_filter

class SegmentationEvolution(QObject):
    def __init__(self,LoadMRI,SegInitialization,Threshold,button,spin_iterations):
        super().__init__()

        self.LoadMRI = LoadMRI
        self.SegInit = SegInitialization
        self.Thres = Threshold
        self.th_img = self.LoadMRI.th_img
        self.actor_bubble = self.SegInit.actor_bubble
        self.button  = button
        self.spin_iterations = spin_iterations

        self._play_icon  = button.style().standardIcon(QStyle.SP_MediaPlay)
        self._pause_icon = button.style().standardIcon(QStyle.SP_MediaPause)

        self.thread  = None
        self.worker  = None
        self.running = False

        self.last_phi   = None   # sitk.Image, signed level-set state
        self.last_speed = None

        self.evolution_actors = {}
        self.evolved_actors = {
            'coronal': [],
            'axial': [],
            'sagittal': []
        }

        # TO BE ADJUSTED
        self.BALLOON      = 3.0 #8.0 (7.5: stuck at 104599)
        self.CURVATURE    = 0.3 #0.3
        self.ADVECTION    = 1.5 #1.5


        self.MAX_ITERS    = 5000
        self.CHUNK        = 10 #25
        self.RMS_TOL      = 1e-5
        self.total_iterations = 0

        ## create_initialwrapper
        #self.ls_array = self.initialize_level_set()
        #for vn in 'axial','coronal','sagittal':
        #    self.visualize_level_set(vn,self.ls_array,255)

        ##make selected circle lines invisible
        for i in 0,1,2:
            actor_cirlce = self.SegInit.actor_selected[i]
            actor_cirlce[2].SetVisibility(0)

        ## make circles invisible
        for i,[_, actor,center,radius,c_px,_] in enumerate(self.SegInit.actor_bubble):
            actor.SetVisibility(0)
            actor.SetVisibility(0)
            actor_cirlce = self.SegInit.actor_selected[i]
            actor_cirlce[2].SetVisibility(0)

        button.clicked.connect(self.on_play_pause)
        #button.clicked.connect(lambda val: self.LoadMRI.SegEvolution.evolve())

    def on_play_pause(self):
        if self.running:
            self.button.setIcon(self._pause_icon)
            self.stop_evolution()
        else:
            self.button.setIcon(self._play_icon)
            self.start_evolution()


    def bubbles_to_initial_levelset(self,shape_zyx, spacing_xyz, bubbles):
        sx, sy, sz = spacing_xyz
        zz, yy, xx = np.indices(shape_zyx).astype(np.float32)
        inside = np.zeros(shape_zyx, dtype=bool)
        for cz, cy, cx, r in bubbles:
            d2 = ((zz - cz)*sz)**2 + ((yy - cy)*sy)**2 + ((xx - cx)*sx)**2
            inside |= d2 <= r*r
        # signed distance: negative inside, positive outside
        dist_out = ndi.distance_transform_edt(~inside, sampling=(sz, sy, sx))
        dist_in  = ndi.distance_transform_edt( inside, sampling=(sz, sy, sx))
        phi = (dist_out - dist_in).astype(np.float32)
        phi_img = sitk.GetImageFromArray(phi)
        phi_img.SetSpacing(spacing_xyz)
        return phi_img

    def _build_speed_and_init(self):
        # dedupe (each 3D bubble stored 3× — once per view)
        th = self.LoadMRI.th_img
        print(f"[diag] th_img dtype={th.dtype} shape={th.shape}",flush=True)
        print(f"[diag] th_img min={th.min()} max={th.max()} mean={th.mean():.3f}",flush=True)

        unique = {}
        for view_name, _a, _c, radius, c_px, _ in self.SegInit.actor_bubble:
            unique[(c_px[0], c_px[1], c_px[2], radius)] = None
        bubbles = list(unique.keys())
        if not bubbles:
           return None, None, None, None
        shape_zyx = self.LoadMRI.th_img.shape
        for i, (cz, cy, cx, r) in enumerate(bubbles):
           z, y, x = int(cz), int(cy), int(cx)
           in_bounds = (0 <= z < shape_zyx[0]
                        and 0 <= y < shape_zyx[1]
                        and 0 <= x < shape_zyx[2])
           if in_bounds:
               print(f"[bubble {i}] (z,y,x)=({z},{y},{x}) r={r}  "
                     f"th_img={self.LoadMRI.th_img[z,y,x]}")
           else:
               print(f"[bubble {i}] OUT OF BOUNDS (z,y,x)=({z},{y},{x}) shape={shape_zyx}")

        shape_zyx   = self.LoadMRI.th_img.shape
        spacing_xyz = tuple(self.LoadMRI.volumes[0].spacing[::-1])
        sx, sy, sz  = spacing_xyz

        phi0 = self.bubbles_to_initial_levelset(shape_zyx, spacing_xyz, bubbles)

        ##only thing that changed
        th_smooth = median_filter(self.LoadMRI.th_img, size=3)
        speed_np = th_smooth.astype(np.float32) / 32767.0

        struct_inplane = np.zeros((1, 3, 3), dtype=bool)
        struct_inplane[0] = ndi.generate_binary_structure(2, 1)
        positive = ndi.binary_opening(speed_np > 0,structure=struct_inplane, iterations=8)
        positive = ndi.binary_closing(positive, iterations=1)

        lbl, _ = ndi.label(positive)
        keep = set()
        for cz, cy, cx, r in bubbles:
            l = int(lbl[int(cz), int(cy), int(cx)])
            if l > 0:
                keep.add(l)
        positive = np.isin(lbl, list(keep))

        speed_np = np.where(positive, speed_np, -1.0).astype(np.float32)
        speed = sitk.GetImageFromArray(speed_np)
        speed.SetSpacing([spacing_xyz[0],spacing_xyz[1],spacing_xyz[0]*2])#spacing_xyz)
        phi0.SetSpacing([spacing_xyz[0],spacing_xyz[1],spacing_xyz[0]*2])
        print(spacing_xyz,shape_zyx,flush=True)

        return phi0, speed, bubbles, shape_zyx

    def _postprocess(self, mask_bool,min_voxels=20, min_mean_speed=0.1):
        #m = ndi.binary_opening(mask_bool, iterations=1)
        #m = ndi.binary_closing(m, iterations=1)
        m = mask_bool
        lbl, n = ndi.label(m)
        if n > 1:
            # mean speed value per component
            sizes = ndi.sum(m, lbl, range(1, n + 1))
            speed = self.LoadMRI.th_img.astype(np.float32) / 32767.0
            mean_speed = ndi.mean(speed, lbl, range(1, n + 1))

            keep = np.where(
                (sizes >= min_voxels) & (mean_speed > min_mean_speed)
            )[0] + 1
            m = np.isin(lbl, keep)
        m = ndi.binary_fill_holes(m)

        return m.astype(bool)

    # -------- play / stop --------
    def start_evolution(self):
        self.running = True
        if self.thread is not None:
            return  # already running

        if self.last_phi is not None and self.last_speed is not None:
            phi0, speed = self.last_phi, self.last_speed
        else:
            phi0, speed, _,_ = self._build_speed_and_init() #bubbles, shape_zyx
            self.last_phi   = phi0
            self.last_speed = speed

        if phi0 is None:
            return

        params = {
            "balloon":   self.BALLOON,
            "curvature": self.CURVATURE,
            "advection": self.ADVECTION,
            "rms_tol":   self.RMS_TOL,
            "chunk":     self.CHUNK,
            "max_iters": self.MAX_ITERS,
        }

        self.thread = QThread()
        self.worker = EvolutionWorker(self,phi0, speed, params, self.total_iterations)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(lambda msg: print("Evolution error:", msg))

        # proper cleanup: wait until the thread actually exits before nulling refs
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.finished.connect(self._after_thread_stopped)

        self.thread.start()


    def stop_evolution(self):
        if self.worker is not None:
            self.worker.abort()

    @Slot()
    def _after_thread_stopped(self):
        if self.worker is not None:
            self.worker.deleteLater()
        if self.thread is not None:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None

    # -------- slots (run on GUI thread) --------
    @Slot(object)
    def on_progress(self, mask,phi,iterations):
        self.last_phi = phi
        # live preview during evolution; no post-processing yet
        self.LoadMRI.segmentation_mask = mask
        self.save_mask(mask)
        self.spin_iterations.setValue(iterations)

    @Slot(object)
    def on_finished(self, mask,phi,iterations):
        self.last_phi = phi
        self.running = False
        self.spin_iterations.setValue(iterations)
        self.total_iterations = iterations
        self.button.setIcon(self._pause_icon)
        self.LoadMRI.segmentation_mask = mask
        self.save_mask(mask,visualisation_3d=True)


    # -------- save --------
    def save_mask(self,mask,visualisation_3d=False):
        mask = self._postprocess(mask)
        self.LoadMRI.segmentation_mask = mask
        if mask is None:
            return
        img = sitk.GetImageFromArray(mask.astype(np.uint8))
        img.CopyInformation(self.LoadMRI.volumes[0].ref_image)
        sitk.WriteImage(img, '/home/neurox/Downloads/MRID data/anat/segmentation.nii.gz')
        z, y, x = self.LoadMRI.slice_indices[0].copy()
        self.visualize(mask[z, :, :], self.LoadMRI.vtk_widgets[0]["axial"], "axial")
        self.visualize(mask[:, y, :], self.LoadMRI.vtk_widgets[0]["coronal"], "coronal")
        self.visualize(np.fliplr(mask[:, :, x].T), self.LoadMRI.vtk_widgets[0]["sagittal"], "sagittal")
        if visualisation_3d:
            self.visualize_3d( mask, self.LoadMRI.SegEvolution.vtkwidget_3d)


    def update_evolution_initializtion(self):
        mask = self.LoadMRI.segmentation_mask
        z, y, x = self.LoadMRI.slice_indices[0].copy()
        self.visualize(mask[z, :, :], self.LoadMRI.vtk_widgets[0]["axial"], "axial")
        self.visualize(mask[:, y, :], self.LoadMRI.vtk_widgets[0]["coronal"], "coronal")
        self.visualize(np.fliplr(mask[:, :, x].T), self.LoadMRI.vtk_widgets[0]["sagittal"], "sagittal")
        #for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
        #    for view_name, widget in vtk_widget_image.items():
        #        widget.GetRenderWindow().Render()

    def visualize_3d(self, mask, vtk_widget):
        """Render the mask as a 3D isosurface in a QVTKRenderWindowInteractor."""
        # 1. numpy → vtkImageData
        m = np.ascontiguousarray(mask.astype(np.uint8))   # (Nz, Ny, Nx), x fastest — good
        nz, ny, nx = m.shape

        importer = vtk.vtkImageImport()
        importer.SetDataScalarTypeToUnsignedChar()
        importer.SetNumberOfScalarComponents(1)
        importer.SetWholeExtent(0, nx - 1, 0, ny - 1, 0, nz - 1)
        importer.SetDataExtentToWholeExtent()

        # spacing in (x, y, z) order
        spacing = self.LoadMRI.volumes[0].spacing[::-1]
        importer.SetDataSpacing(spacing)
        importer.SetDataOrigin(self.LoadMRI.volumes[0].ref_image.GetOrigin())

        # numpy is (z, y, x) contiguous; VTK expects x fastest → transpose
        importer.CopyImportVoidPointer(m.tobytes(), m.nbytes)
        importer.Update()

        # 2. Marching cubes — isosurface at 0.5 gives the boundary of the binary
        mc = vtk.vtkDiscreteMarchingCubes()
        mc.SetInputConnection(importer.GetOutputPort())
        mc.GenerateValues(1, 1, 1)   # extract label 1
        mc.Update()

        # 4. Mapper + actor
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(mc.GetOutputPort())
        mapper.ScalarVisibilityOff()

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.85, 0.30, 0.30)  # red-ish
        actor.GetProperty().SetOpacity(1.0)

        # 5. Renderer
        renderer = vtk.vtkRenderer()
        renderer.SetBackground(0.1, 0.1, 0.1)
        renderer.AddActor(actor)
        renderer.ResetCamera()

        rw = vtk_widget.GetRenderWindow()
        # remove any old renderers so repeated calls don't stack
        while rw.GetRenderers().GetNumberOfItems() > 0:
            rw.RemoveRenderer(rw.GetRenderers().GetFirstRenderer())
        rw.AddRenderer(renderer)
        vtk_widget.GetRenderWindow().Render()

        # keep a reference to prevent GC
        self._3d_actor    = actor
        self._3d_renderer = renderer


    def visualize(self, evolved_slice, vtk_widget, view_name):
        """
        Visualize only the evolved bubbles as red overlay in VTK.


        Parameters:
        - evolved_slice: 2D numpy array of the slice (negative = inside bubble)
        - vtk_widget: the corresponding VTK widget
        - view_name: string name for the view ("axial", "coronal", "sagittal")
        """
        h, w = evolved_slice.shape

        # Create empty RGB image (black background)
        rgba = np.zeros((h, w, 4), dtype=np.uint8)

        # Bubble mask: negative values are inside
        #bubble_mask = evolved_slice < 0
        bubble_mask = evolved_slice.astype(bool)

        # Color bubbles red
        rgba[bubble_mask, 0] = 255  # R
        rgba[bubble_mask, 1] = 0    # G
        rgba[bubble_mask, 2] = 0    # B
        rgba[bubble_mask, 3] = 180    # A

        # Convert to VTK image
        #vtk_data = numpy_support.numpy_to_vtk(rgb.ravel(), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
        #img_vtk = vtk.vtkImageData()
        #img_vtk.SetDimensions(w, h, 1)
        #img_vtk.GetPointData().SetScalars(vtk_data)
        #img_vtk.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)  # RGB
        importer = vtk.vtkImageImport()
        importer.SetDataScalarTypeToUnsignedChar()
        importer.SetNumberOfScalarComponents(4)
        importer.SetWholeExtent(0, w - 1, 0, h - 1, 0, 0)
        importer.SetDataExtentToWholeExtent()
        rgba_bytes = rgba.tobytes()
        importer.CopyImportVoidPointer(rgba_bytes, len(rgba_bytes))

        # Correct spacing per view
        if view_name == "axial":      # z fixed -> (y,x)
            spacing = (self.LoadMRI.volumes[0].spacing[2], self.LoadMRI.volumes[0].spacing[1], 1.0)
        elif view_name == "coronal": # y fixed -> (z,x)
            spacing = (self.LoadMRI.volumes[0].spacing[2], self.LoadMRI.volumes[0].spacing[0], 1.0)
        elif view_name == "sagittal":# x fixed -> (z,y)
            spacing = (self.LoadMRI.volumes[0].spacing[0], self.LoadMRI.volumes[0].spacing[1], 1.0)
        importer.SetDataSpacing(spacing)
        importer.SetDataOrigin(0.0, 0.0, 0.01)   # tiny nudge to win Z-fight
        importer.Update()

        # Create actor
        renderer = self.LoadMRI.renderers[0][view_name]
        old = self.evolved_actors.get(view_name)
        if isinstance(old, vtk.vtkImageActor):
            renderer.RemoveActor(old)

        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputData(importer.GetOutput()) #img_vtk)

        # Add actor to renderer
        renderer.AddActor(actor)
        #renderer.ResetCamera()

        vtk_widget.GetRenderWindow().Render()

        # Keep reference
        self.evolved_actors[view_name] = actor

class EvolutionWorker(QObject):
    progress = Signal(object,object,object)   # emits current mask (numpy bool array)
    finished = Signal(object,object,object)   # emits final mask
    error    = Signal(str)

    def __init__(self, SegmentationEvolution, phi0, speed, params,total_iter):
        super().__init__()
        self.SegmentationEvolution = SegmentationEvolution
        self.phi0   = phi0
        self.speed  = speed
        self.params = params
        self._abort = False
        self.last_total = total_iter

    @Slot()
    def abort(self):
        self._abort = True

    @Slot()
    def run(self):
        try:
            p = self.params
            gac = sitk.GeodesicActiveContourLevelSetImageFilter()
            gac.SetPropagationScaling(p["balloon"])
            gac.SetCurvatureScaling(p["curvature"])
            gac.SetAdvectionScaling(p["advection"])
            gac.SetMaximumRMSError(p["rms_tol"])
            gac.SetNumberOfIterations(p["chunk"])
            gac.AddCommand(sitk.sitkIterationEvent, lambda: self.on_iter(gac))

            phi = self.phi0
            total = self.last_total
            while total < p["max_iters"] and not self._abort:
                phi = gac.Execute(phi, self.speed)
                total += gac.GetElapsedIterations()
                self.mask = sitk.GetArrayFromImage(phi) < 0
                self.progress.emit(self.mask,phi,total)
                print(f"[worker] iter={total}  rms={gac.GetRMSChange():.5f}  voxels={int(self.mask.sum())}",flush=True)
                if gac.GetElapsedIterations() < p["chunk"]:
                    break  # converged

            final = sitk.GetArrayFromImage(phi) < 0
            self.finished.emit(final,phi,total)
        except Exception as e:
            self.error.emit(str(e))

    def on_iter(self, filter):
        it = filter.GetElapsedIterations()
        if it % 20 == 0:
            print(f"iter {it}  rms={filter.GetRMSChange():.5f}", flush=True)
        #