# This Python file uses the following encoding: utf-8
from core.segmentation.threshold import ThresholdSegmentation
from core.segmentation.initialization import SegmentationInitialization
from core.segmentation.evolution import SegmentationEvolution

class SegmentationGUI:
    """
    ---------------------------------------------
    !!!AT THE MOMENT NO ACTIVE PART OF THE GUI!!!
    ---------------------------------------------

    The SegmentationGUI class connects the segmentation workflow (thresholding, bubble initialization,
    and level-set evolution) to the application's Qt UI.

    The segmentation is not yet finished.

    Parameters
    ----------
    MW : object
        The main window instance containing the Qt UI and MRI data management (LoadMRI).
    """
    def __init__(self,MW):
        """Initialize the segmentation GUI and connect UI elements to corresponding handlers."""
        self.ui = MW.ui
        self.ui.checkBox_threshold.stateChanged.connect(self.on_threshold_changed)
        self.ui.pushButton_Next1.clicked.connect(self.active_bubbles)
        self.ui.pushButton_Back2.clicked.connect(self.threshold_seg)
        self.ui.pushButton_Next2.clicked.connect(self.evolution)
        self.ui.pushButton_Back3.clicked.connect(self.active_bubbles)
        #self.ui.pushButton_Finish.clicked.connect(self.seg_finsih)

    def on_threshold_changed(self, checked:bool):
        """
            Toggle thresholding on/off and update UI and data accordingly.
            When enabled, threshold segmentation is initialized and its parameters (upper/lower bounds)
            are linked to spinboxes and scrollbars in the UI.
        """
        if checked:  # If true, original images not needed
            self.LoadMRI.threshold_on = True
            #Segmentation
            self.LoadMRI.Threshold = ThresholdSegmentation(self.LoadMRI)
            #threshold limits
            self.ui.doubleSpinBox_lower.setValue(self.LoadMRI.Threshold.lower)
            self.ui.ScrollBar_lower.setValue(self.LoadMRI.Threshold.lower)
            self.ui.doubleSpinBox_upper.setValue(self.LoadMRI.Threshold.upper)
            self.ui.ScrollBar_upper.setValue(self.LoadMRI.Threshold.upper)
            self.ui.doubleSpinBox_lower.setRange(0,int(self.LoadMRI.volume[self.LoadMRI.thres_idx][0].max())+1)
            self.ui.ScrollBar_lower.setRange(0,int(self.LoadMRI.volume[self.LoadMRI.thres_idx][0].max())+1)
            self.ui.doubleSpinBox_upper.setRange(0,int(self.LoadMRI.volume[self.LoadMRI.thres_idx][0].max())+1)
            self.ui.ScrollBar_upper.setRange(0,int(self.LoadMRI.volume[self.LoadMRI.thres_idx][0].max())+1)
            self.ui.doubleSpinBox_lower.valueChanged.connect(self.on_spin_changed_lower)
            self.ui.ScrollBar_lower.valueChanged.connect(self.on_scroll_changed_lower)
            self.ui.doubleSpinBox_upper.valueChanged.connect(self.on_spin_changed_upper)
            self.ui.ScrollBar_upper.valueChanged.connect(self.on_scroll_changed_upper)

            #threshold buttons
            self.ui.radioButton_bounded.toggled.connect(
                lambda checked: (setattr(self.LoadMRI.Threshold, 'threshold_mode', 'bounded'), self.update_threshold_display()) if checked else None
            )
            self.ui.radioButton_lower.toggled.connect(
                lambda checked: (setattr(self.LoadMRI.Threshold, 'threshold_mode', 'lower'), self.update_threshold_display()) if checked else None
            )
            self.ui.radioButton_upper.toggled.connect(
                lambda checked: (setattr(self.LoadMRI.Threshold, 'threshold_mode', 'upper'), self.update_threshold_display()) if checked else None
            )

            #threshold ON/OFF
            self.ui.checkBox_threshold.setText("Threshold ON")
            self.update_threshold_display()
            self.LoadMRI.intensity_table.update_table("Threshold",0)
        else:  # If false, original images needed and loaded incase indexes have changed
            self.LoadMRI.threshold_on = False
            self.ui.checkBox_threshold.setText("Threshold OFF")
            for _,vtk_widget_image in self.LoadMRI.vtk_widgets.items():
                for view_name, widget in vtk_widget_image.items():
                    if view_name in self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx]:
                        renderer = self.LoadMRI.renderers[0][view_name]
                        renderer.RemoveActor(self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx][view_name])
                        del self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx][view_name]
                        widget.GetRenderWindow().Render()

            self.LoadMRI.volume[self.LoadMRI.thres_idx] = {}
            ##if more files!!!
            self.LoadMRI.actors_non_mainimage[self.LoadMRI.thres_idx] = {}
            self.LoadMRI.intensity_table.update_table("Threshold",0)
            self.LoadMRI.update_slices(0)


    def threshold_seg(self):
        """Display the threshold adjustment page."""
        self.ui.stackedWidget.setCurrentIndex(0)
        self.update_threshold_display()


    def update_threshold_display(self):
        """Refresh the thresholded image display according to current mode and bounds."""
        if self.LoadMRI.Threshold.threshold_mode == 'bounded':
            self.LoadMRI.th_img = self.LoadMRI.Threshold.smooth_binary_threshold(self.LoadMRI.volume[self.LoadMRI.thres_idx][0], lower=self.LoadMRI.Threshold.lower, upper=self.LoadMRI.Threshold.upper)
            self.ui.ScrollBar_lower.setEnabled(True)
            self.ui.doubleSpinBox_lower.setEnabled(True)
            self.ui.ScrollBar_upper.setEnabled(True)
            self.ui.doubleSpinBox_upper.setEnabled(True)
        elif self.LoadMRI.Threshold.threshold_mode == 'lower':
            self.LoadMRI.th_img = self.LoadMRI.Threshold.smooth_binary_threshold(self.LoadMRI.volume[self.LoadMRI.thres_idx][0], lower=self.LoadMRI.Threshold.lower, upper=None)
            self.ui.ScrollBar_lower.setEnabled(True)
            self.ui.doubleSpinBox_lower.setEnabled(True)
            self.ui.ScrollBar_upper.setEnabled(False)
            self.ui.doubleSpinBox_upper.setEnabled(False)
        elif self.LoadMRI.Threshold.threshold_mode == 'upper':
            self.LoadMRI.th_img = self.LoadMRI.Threshold.smooth_binary_threshold(self.LoadMRI.volume[self.LoadMRI.thres_idx][0], lower=None, upper=self.LoadMRI.Threshold.upper)
            self.ui.ScrollBar_lower.setEnabled(False)
            self.ui.doubleSpinBox_lower.setEnabled(False)
            self.ui.ScrollBar_upper.setEnabled(True)
            self.ui.doubleSpinBox_upper.setEnabled(True)
        self.LoadMRI.Threshold.only_update_displayed_image()

    # --- Synchronize UI values for lower/upper threshold bounds ---
    def on_spin_changed_lower(self,val):
        self.LoadMRI.Threshold.lower = val
        self.ui.ScrollBar_lower.setValue(self.LoadMRI.Threshold.lower)
        self.check_rangeLow()
        self.update_threshold_display()

    def on_spin_changed_upper(self,val):
        self.LoadMRI.Threshold.upper = val
        self.ui.ScrollBar_upper.setValue(self.LoadMRI.Threshold.upper)
        self.check_rangeUp()
        self.update_threshold_display()

    def on_scroll_changed_lower(self,val):
        self.LoadMRI.Threshold.lower = val
        self.ui.doubleSpinBox_lower.setValue(self.LoadMRI.Threshold.lower)
        self.check_rangeLow()
        self.update_threshold_display()

    def on_scroll_changed_upper(self,val):
        self.LoadMRI.Threshold.upper = val
        self.ui.doubleSpinBox_upper.setValue(self.LoadMRI.Threshold.upper)
        self.check_rangeUp()
        self.update_threshold_display()

    def check_rangeUp(self):
        """Ensure upper bound >= lower bound."""
        if self.LoadMRI.Threshold.upper < self.LoadMRI.Threshold.lower:
            self.LoadMRI.Threshold.lower = self.LoadMRI.Threshold.upper
            self.ui.doubleSpinBox_lower.setValue(self.LoadMRI.Threshold.lower)
            self.ui.ScrollBar_lower.setValue(self.LoadMRI.Threshold.lower)

    def check_rangeLow(self):
        """Ensure upper bound >= lower bound."""
        if self.LoadMRI.Threshold.lower > self.LoadMRI.Threshold.upper:
            self.LoadMRI.Threshold.upper = self.LoadMRI.Threshold.lower
            self.ui.doubleSpinBox_upper.setValue(self.LoadMRI.Threshold.upper)
            self.ui.ScrollBar_upper.setValue(self.LoadMRI.Threshold.upper)


    def active_bubbles(self):
        """
            Switch to the bubble initialization page.
            Creates a table for bubble management and connects UI elements
            for radius control and bubble addition/removal.
        """
        self.ui.stackedWidget.setCurrentIndex(1)
        if self.initialization_first_time:
            #Get radius
            self.LoadMRI.SegInitialization = SegmentationInitialization(self.LoadMRI)
            table = self.ui.tableView_activeBub
            self.LoadMRI.SegInitialization.create_table(table)
            self.LoadMRI.SegInitialization.radius = 2
            self.ui.doubleSpinBox_Bubradius.setValue(self.LoadMRI.SegInitialization.radius)
            self.ui.horizontalSlider_Bubradius.setValue(self.LoadMRI.SegInitialization.radius*100)
            self.ui.doubleSpinBox_Bubradius.setRange(0.01,6)
            self.ui.horizontalSlider_Bubradius.setRange(1,6*100)
            self.ui.doubleSpinBox_Bubradius.valueChanged.connect(lambda val: self.get_bubble_radius('SpinBox',val=val))
            self.ui.horizontalSlider_Bubradius.valueChanged.connect(lambda val: self.get_bubble_radius('Slider',val=val))
            self.ui.pushButton_addBubbles.clicked.connect(lambda val: self.LoadMRI.SegInitialization.draw_bubble(self.ui.pushButton_Next2))
            #info if row in table is selected
            self.ui.tableView_activeBub.selectionModel().selectionChanged.connect(self.LoadMRI.SegInitialization.row_selected)
            #delete bubble
            self.ui.pushButton_delete.clicked.connect(self.delete_bubble)

            self.initialization_first_time = False
        else:
            self.LoadMRI.SegInitialization.table.show()



    def delete_bubble(self):
        """
            Delete the currently selected bubble from the visualization and table.
            Ensures both the actor and data model are updated consistently.
        """
        for i,[view_name,actor,_,_,_,_] in enumerate(self.LoadMRI.SegInitialization.actor_bubble):
            #remove from renderer
            if int(i/3) == self.LoadMRI.SegInitialization.row_index:
                renderer = self.LoadMRI.renderers[0][view_name]
                renderer.RemoveActor(actor)

                actor_entry = self.LoadMRI.SegInitialization.actor_selected[i]
                renderer.RemoveActor(actor_entry[2])

        #remove from list (3 enteries)
        self.LoadMRI.SegInitialization.actor_bubble.pop(self.LoadMRI.SegInitialization.row_index*3+2)
        self.LoadMRI.SegInitialization.actor_bubble.pop(self.LoadMRI.SegInitialization.row_index*3+1)
        self.LoadMRI.SegInitialization.actor_bubble.pop(self.LoadMRI.SegInitialization.row_index*3)
        self.LoadMRI.SegInitialization.actor_selected.pop(self.LoadMRI.SegInitialization.row_index*3+2)
        self.LoadMRI.SegInitialization.actor_selected.pop(self.LoadMRI.SegInitialization.row_index*3+1)
        self.LoadMRI.SegInitialization.actor_selected.pop(self.LoadMRI.SegInitialization.row_index*3)
        self.LoadMRI.SegInitialization.index -= 1

        #remove from table
        self.ui.tableView_activeBub.selectionModel().selectionChanged.disconnect(self.LoadMRI.SegInitialization.row_selected)
        self.LoadMRI.SegInitialization.model.removeRow(self.LoadMRI.SegInitialization.row_index)
        self.ui.tableView_activeBub.selectionModel().selectionChanged.connect(self.LoadMRI.SegInitialization.row_selected)

        self.LoadMRI.SegInitialization.row_index = min(self.LoadMRI.SegInitialization.row_index, self.LoadMRI.SegInitialization.model.rowCount()-1)
        self.LoadMRI.SegInitialization.update_bubbles_visible()
        for view_name in 'axial','coronal','sagittal':
            self.LoadMRI.renderers[0][view_name].GetRenderWindow().Render()
        if self.LoadMRI.SegInitialization.model.rowCount() == 0:
            self.ui.pushButton_Next2.setEnabled(False)


    def get_bubble_radius(self,mode,val):
        """
            Sync bubble radius between spinbox and slider and update visual bubbles.
            Parameters
            ----------
            mode : str
                'SpinBox' or 'Slider'
            val : float
                The new radius value (in mm)
        """
        if mode == 'SpinBox':
            self.LoadMRI.SegInitialization.radius = val
            self.ui.horizontalSlider_Bubradius.setEnabled(False)
            self.ui.horizontalSlider_Bubradius.setValue(int(self.LoadMRI.SegInitialization.radius*100))
            self.ui.horizontalSlider_Bubradius.setEnabled(True)
        elif mode == 'Slider':
            self.LoadMRI.SegInitialization.radius = val /100
            self.ui.doubleSpinBox_Bubradius.setEnabled(False)
            self.ui.doubleSpinBox_Bubradius.setValue(self.LoadMRI.SegInitialization.radius)
            self.ui.doubleSpinBox_Bubradius.setEnabled(True)

        if self.LoadMRI.SegInitialization.selected:
            for i in 0,1,2:
                self.LoadMRI.SegInitialization.actor_bubble[self.LoadMRI.SegInitialization.row_index*3+i][3] = self.LoadMRI.SegInitialization.radius
            self.LoadMRI.SegInitialization.update_bubbles_visible()
            self.LoadMRI.SegInitialization.model.setItem(self.LoadMRI.SegInitialization.row_index,3, QStandardItem(str(self.LoadMRI.SegInitialization.radius)))


    def evolution(self):
        """
            Switch to the segmentation evolution page and initialize the
            level-set (or bubble evolution) process.

            TODO: still in process
        """
        self.ui.stackedWidget.setCurrentIndex(2)
        #if self.evolution_first_time:
            # SChange button icons: play, pause
        button = self.ui.toolButton_runEvo
        self.LoadMRI.SegEvolution = SegmentationEvolution(self.LoadMRI,self.LoadMRI.SegInitialization,self.LoadMRI.Threshold,button)
        self.ui.toolButton_runEvo.clicked.connect(self.LoadMRI.SegEvolution.initialize_segmentation_itk)
        #    self.evolution_first_time = False
        #else:
        #    self.load_mri.SegEvolution.new_evolution()





