import os
import shutil
import tempfile

import numpy as np
from astropy.table import Table
from astropy import units as u


DATA = """
source_1 0.0 0.0 1 1 1 0.2 0.1 1.3 0.2 1.5 0.3
source_2 0.0 0.0 1 1 1 0.2 0.05 1.2 0.1 1.8 0.3
"""

def generate_random_models(models_dir, aperture_dependent=False):

    # Create fake SEDs
    np.random.seed(12345)
    os.mkdir(os.path.join(models_dir, 'seds'))

    names = []

    for i in range(5):

        from ..sed import SED

        sed = SED()

        sed.name = 'model_{0:04d}'.format(i)
        sed.distance = 1 * u.kpc
        sed.wav = np.logspace(-2., 3., 100) * u.micron
        sed.nu = sed.wav.to(u.Hz, equivalencies=u.spectral())

        if aperture_dependent:
            sed.apertures = np.logspace(1., 6., 10) * u.au
            sed.flux = np.cumsum(np.random.random((10, 100)), axis=0) * u.mJy
        else:
            sed.apertures = None
            sed.flux = (1 + np.random.random((1,100))) * u.mJy

        sed.error = sed.flux * np.random.random(100) / 100.

        sed.write(os.path.join(models_dir, 'seds', sed.name + '_sed.fits'))

        names.append(sed.name)

    # Generate model conf file
    f = open(os.path.join(models_dir, 'models.conf'), 'w')
    f.write("name = test\n")
    f.write("length_subdir = 0\n")
    f.write("aperture_dependent = {0}\n".format('yes' if aperture_dependent else 'no'))
    f.write("logd_step = 0.02\n")
    f.close()

    # Generate model parameter file
    t = Table()
    t['MODEL_NAME'] = np.array(names, dtype='S30')
    t['par1'] = np.random.random(5)
    t['par2'] = np.random.random(5)
    t.write(os.path.join(models_dir, 'parameters.fits'))


class BasePipelineTest(object):

    def setup_class(self):

        self.tmpdir = tempfile.mkdtemp()
        generate_random_models(self.tmpdir, aperture_dependent=self.aperture_dependent)

    def teardown_class(self):
        shutil.rmtree(self.tmpdir)

    def test_full_pipeline(self, tmpdir):

        from ..convolve import convolve_model_dir
        from ..filter import Filter

        np.random.seed(12345)

        f1 = Filter()
        f1.name = 'alice'
        f1.wavelength = 7.
        f1.wav = np.linspace(5., 1., 100) * u.micron
        f1.nu = f1.wav.to(u.Hz, equivalencies=u.spectral())
        f1.r = np.random.random(100)
        f1.normalize()

        f2 = Filter()
        f2.name = 'bob'
        f2.wavelength = 12.
        f2.wav = np.linspace(15., 10., 100) * u.micron
        f2.nu = f2.wav.to(u.Hz, equivalencies=u.spectral())
        f2.r = np.random.random(100)
        f2.normalize()

        f3 = Filter()
        f3.name = 'eve'
        f3.wavelength = 20.
        f3.wav = np.linspace(25., 15., 100) * u.micron
        f3.nu = f3.wav.to(u.Hz, equivalencies=u.spectral())
        f3.r = np.random.random(100)
        f3.normalize()

        convolve_model_dir(self.tmpdir, filters=[f1, f2, f3], overwrite=True)

        from ..extinction import Extinction

        extinction = Extinction()
        extinction.wav = np.logspace(-2., 3.)
        extinction.chi = extinction.wav ** -2

        from ..fit import fit

        data_file = tmpdir.join('data').strpath
        open(data_file, 'w').write(DATA.strip())

        output_file = tmpdir.join('output').strpath

        fit(data_file, ['bob', 'alice', 'eve'], [1., 3., 3.], self.tmpdir, output_file,
            extinction_law=extinction,
            distance_range=[1., 2.],
            av_range=[0., 0.1],
            output_format=('F', 3.),
            output_convolved=False)

        from ..plot import plot

        plots_dir = tmpdir.join('plots_sed_auto').strpath

        plot(output_file,
            plot_mode='A',
            output_dir=plots_dir,
            select_format=('F', 3.),
            format='png')

        plots_dir = tmpdir.join('plots_sed_manual').strpath

        plot(output_file,
            plot_mode='A',
            output_dir=plots_dir,
            select_format=('F', 3.),
            format='png',
            show_convolved=False, show_sed=True,
            x_mode='M', x_range=(0.1, 2000),
            y_mode='M', y_range=(1.e-14, 2e-8),
            plot_max=100)

        from ..plot_params_1d import plot_params_1d

        plots_dir = tmpdir.join('plots_1d').strpath

        plot_params_1d(output_file, 'par1',
                       log_x=True,
                       output_dir=plots_dir,
                       select_format=('F', 2.), format='png')

        from ..plot_params_2d import plot_params_2d

        plots_dir = tmpdir.join('plots_2d').strpath

        plot_params_2d(output_file, 'par1', 'par2',
                       log_x=True, log_y=True,
                       output_dir=plots_dir,
                       select_format=('F', 2.), format='png')

        from ..extract_parameters import extract_parameters

        output_prefix = tmpdir.join('extract_parameters').strpath

        extract_parameters(output_file, output_prefix)

        from ..write_parameters import write_parameters

        output_ascii_file = tmpdir.join('write_parameters').strpath

        write_parameters(output_file, output_ascii_file)

        from ..write_parameter_ranges import write_parameter_ranges

        output_ascii_file = tmpdir.join('write_parameters_ranges').strpath

        write_parameter_ranges(output_file, output_ascii_file)


class TestApertureIndependentPipeline(BasePipelineTest):
    aperture_dependent = False


class TestApertureDependentPipeline(BasePipelineTest):
    aperture_dependent = True