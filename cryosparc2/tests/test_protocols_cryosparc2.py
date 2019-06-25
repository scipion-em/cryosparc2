# **************************************************************************
# *
# * Authors: Yunior C. Fonseca Reyna    (cfonseca@cnb.csic.es)
# *
# *
# * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************

from pyworkflow.em.protocol import *
from pyworkflow.tests import *
from pyworkflow.utils import importFromPlugin

from cryosparc2.protocols import *

relionProtocols = importFromPlugin('relion.protocols', doRaise=True)


class TestCryosparcBase(BaseTest):
    @classmethod
    def setData(cls, dataProject='xmipp_tutorial'):
        cls.dataset = DataSet.getDataSet(dataProject)
        cls.micFn = cls.dataset.getFile('allMics')
        cls.volFn = cls.dataset.getFile('vol2')
        cls.partFn1 = cls.dataset.getFile('particles2')
        cls.partFn2 = cls.dataset.getFile('particles3')
        cls.ctfFn = cls.dataset.getFile('ctf')

    @classmethod
    def runImportMicrograph(cls, pattern, samplingRate, voltage,
                            scannedPixelSize, magnification,
                            sphericalAberration):
        """ Run an Import micrograph protocol. """
        # We have two options: pass the SamplingRate or
        # the ScannedPixelSize + microscope magnification
        kwargs = {
            'filesPath': pattern,
            'magnification': magnification,
            'voltage': voltage,
            'sphericalAberration': sphericalAberration
        }

        if samplingRate is not None:
            kwargs.update({'samplingRateMode': 0,
                           'samplingRate': samplingRate})
        else:
            kwargs.update({'samplingRateMode': 1,
                           'scannedPixelSize': scannedPixelSize})

        cls.protImport = ProtImportMicrographs(**kwargs)
        cls.launchProtocol(cls.protImport)

        # Check that input micrographs have been imported
        if cls.protImport.outputMicrographs is None:
            raise Exception('Import of micrograph: %s, failed. '
                            'outputMicrographs is None.' % pattern)

        return cls.protImport

    @classmethod
    def runImportVolumes(cls, pattern, samplingRate,
                         importFrom=ProtImportParticles.IMPORT_FROM_FILES):
        """ Run an Import particles protocol. """
        cls.protImport = cls.newProtocol(ProtImportVolumes,
                                         filesPath=pattern,
                                         samplingRate=samplingRate
                                         )
        cls.launchProtocol(cls.protImport)
        return cls.protImport

    @classmethod
    def runImportParticles(cls, pattern, samplingRate, checkStack=False,
                           importFrom=ProtImportParticles.IMPORT_FROM_FILES):
        """ Run an Import particles protocol. """
        if importFrom == ProtImportParticles.IMPORT_FROM_SCIPION:
            objLabel = 'from scipion (particles)'
        elif importFrom == ProtImportParticles.IMPORT_FROM_FILES:
            objLabel = 'from file (particles)'

        cls.protImport = cls.newProtocol(ProtImportParticles,
                                         objLabel=objLabel,
                                         filesPath=pattern,
                                         sqliteFile=pattern,
                                         samplingRate=samplingRate,
                                         checkStack=checkStack,
                                         importFrom=importFrom)

        cls.launchProtocol(cls.protImport)
        # Check that input images have been imported (a better way to do this?)
        if cls.protImport.outputParticles is None:
            raise Exception('Import of images: %s, failed. '
                            'outputParticles is None.' % pattern)
        return cls.protImport

    @classmethod
    def runImportMicrographBPV(cls, pattern):
        """ Run an Import micrograph protocol. """
        return cls.runImportMicrograph(pattern,
                                       samplingRate=1.237,
                                       voltage=300,
                                       sphericalAberration=2,
                                       scannedPixelSize=None,
                                       magnification=56000)

    @classmethod
    def runImportMicrographRCT(cls, pattern):
        """ Run an Import micrograph protocol. """
        return cls.runImportMicrograph(pattern,
                                       samplingRate=2.28,
                                       voltage=100,
                                       sphericalAberration=2.9,
                                       scannedPixelSize=None,
                                       magnification=50000)

    @classmethod
    def runImportParticleCryoSPARC(cls, pattern):
        """ Run an Import micrograph protocol. """
        return cls.runImportParticles(pattern,
                                      samplingRate=4.,
                                      checkStack=True,
                                      importFrom=ProtImportParticles.IMPORT_FROM_SCIPION)

    @classmethod
    def runImportVolumesCryoSPARC(cls, pattern):
        """ Run an Import micrograph protocol. """
        return cls.runImportVolumes(pattern,
                                    samplingRate=4.,
                                    importFrom=ProtImportParticles.IMPORT_FROM_FILES)


class TestCryosparcClassify2D(TestCryosparcBase):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        setupTestProject(cls)
        dataProject = 'grigorieff'
        dataset = DataSet.getDataSet(dataProject)
        TestCryosparcBase.setData()
        particlesPattern = dataset.getFile('particles.sqlite')
        cls.protImport = cls.runImportParticleCryoSPARC(cls.partFn2)

    def testCryosparc2D(self):
        def _runCryosparcClassify2D(label=''):
            prot2D = self.newProtocol(ProtCryo2D,
                                      doCTF=False, maskDiameterA=340,
                                      numberOfMpi=4, numberOfThreads=1)

            # Normalization after the imported particles
            relionProtocol = self.newProtocol(relionProtocols.ProtRelionPreprocessParticles,
                                        doNormalize=True,
                                        doScale=True, scaleSize=140,
                                        doInvert=False)
            relionProtocol.setObjLabel('relion: preprocess particles')
            relionProtocol.inputParticles.set(self.protImport.outputParticles)
            self.launchProtocol(relionProtocol)

            prot2D.inputParticles.set(relionProtocol.outputParticles)
            prot2D.numberOfClasses.set(5)
            prot2D.numberOnlineEMIterator.set(40)
            prot2D.setObjLabel(label)
            prot2D.numberGPU.set(1)
            self.launchProtocol(prot2D)
            return prot2D

        def _checkAsserts(cryosparcProt):

            self.assertIsNotNone(cryosparcProt.outputClasses,
                                 "There was a problem with Cryosparc 2D classify")

            for class2D in cryosparcProt.outputClasses:
                self.assertTrue(class2D.hasAlignment2D())

        cryosparcProtGpu = _runCryosparcClassify2D(label="Cryosparc classify2D GPU")
        _checkAsserts(cryosparcProtGpu)


class TestCryosparc3DInitialModel(TestCryosparcBase):

    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        setupTestProject(cls)
        dataProject = 'grigorieff'
        dataset = DataSet.getDataSet(dataProject)
        TestCryosparcBase.setData()
        particlesPattern = dataset.getFile('particles.sqlite')
        cls.protImport = cls.runImportParticleCryoSPARC(cls.partFn2)

    def testCryosparcInitialModel(self):
        def _runCryosparcInitialModel(label=''):
            protInitialModel = self.newProtocol(ProtCryoSparcInitialModel,
                                      numberOfMpi=4, numberOfThreads=1)

            # Normalization after the imported particles
            relionProtocol = self.newProtocol(
                relionProtocols.ProtRelionPreprocessParticles,
                doNormalize=True,
                doScale=True, scaleSize=140,
                doInvert=False)
            relionProtocol.setObjLabel('relion: preprocess particles')
            relionProtocol.inputParticles.set(self.protImport.outputParticles)
            self.launchProtocol(relionProtocol)

            protInitialModel.inputParticles.set(relionProtocol.outputParticles)
            protInitialModel.abinit_K.set(1)
            protInitialModel.abinit_symmetry.set('C1')
            protInitialModel.setObjLabel(label)
            self.launchProtocol(protInitialModel)
            return protInitialModel

        def _checkAsserts(cryosparcProt):
            self.assertIsNotNone(cryosparcProt.outputClasses,
                                 "There was a problem with Cryosparc 3D initial model")

            self.assertIsNotNone(cryosparcProt.outputVolumes,
                                 "There was a problem with Cryosparc 3D initial model")

        cryosparcProtGpu = _runCryosparcInitialModel(label="Cryosparc 3D initial model")
        _checkAsserts(cryosparcProtGpu)

