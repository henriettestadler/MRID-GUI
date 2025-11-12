# This Python file uses the following encoding: utf-8
import SimpleITK as sitk

### This class is not yet finished and perfected.
### TODO: check and improve registration, so it works like ITKsnap Rigid Registration


class Registration:
    def __init__(self,LoadMRI):
        self.LoadMRI = LoadMRI
        self.fixed_image = self.LoadMRI.image[0]
        self.moving_image = self.LoadMRI.image[1]

        self.coarest = 4
        self.finest = 1

        self.rigid_transformation()



    def rigid_transformation(self):
        # Initialize with a rigid transform
        initial_transform = sitk.CenteredTransformInitializer(
            self.fixed_image,
            self.moving_image,
            sitk.Euler3DTransform(), # or Euler2DTransform for 2D
            sitk.CenteredTransformInitializerFilter.GEOMETRY
        )
        # Registration method
        registration = sitk.ImageRegistrationMethod()
        # Metric
        registration.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
        registration.SetMetricSamplingStrategy(registration.RANDOM)
        registration.SetMetricSamplingPercentage(1.0)
        # Optimizer
        registration.SetOptimizerAsGradientDescent(
            learningRate=1.0,
            numberOfIterations=300,
            convergenceMinimumValue=1e-6,
            convergenceWindowSize=10
        )
        registration.SetOptimizerScalesFromPhysicalShift()
        # Interpolator
        registration.SetInterpolator(sitk.sitkLinear)
        # Multi-resolution (4× → 1×)
        registration.SetShrinkFactorsPerLevel([4, 2, 1])
        registration.SetSmoothingSigmasPerLevel([2, 1, 0])
        registration.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
        # Initial transform
        registration.SetInitialTransform(initial_transform, inPlace=False)
        # Run it
        final_transform = registration.Execute(self.fixed_image, self.moving_image)
        rigid = final_transform.GetNthTransform(final_transform.GetNumberOfTransforms() - 1)
        # Convert to 12 Parameters and save transform
        sitk.WriteTransform(rigid, "rigid_transform.txt")
        affine = sitk.AffineTransform(rigid.GetDimension())
        affine.SetMatrix(rigid.GetMatrix())
        affine.SetTranslation(rigid.GetTranslation())
        affine.SetCenter(rigid.GetCenter())
        sitk.WriteTransform(affine, "rigid_affine_style.txt")

        # get the ind_0 and ind_7 out of the filename!!!


