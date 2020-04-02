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

from pwem.protocols import *
from pyworkflow.tests import *
from pwem import Domain

from ..protocols import *
from ..constants import *
from ..utils import calculateNewSamplingRate


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

        protImportMic = ProtImportMicrographs(**kwargs)
        cls.launchProtocol(protImportMic)

        # Check that input micrographs have been imported
        if protImportMic.outputMicrographs is None:
            raise Exception('Import of micrograph: %s, failed. '
                            'outputMicrographs is None.' % pattern)

        return protImportMic

    @classmethod
    def runImportVolumes(cls, pattern, samplingRate,
                         importFrom=ProtImportParticles.IMPORT_FROM_FILES):
        """ Run an Import volumes protocol. """
        protImportVol = cls.newProtocol(ProtImportVolumes,
                                         filesPath=pattern,
                                         samplingRate=samplingRate
                                         )
        cls.launchProtocol(protImportVol)
        return protImportVol

    @classmethod
    def runImportParticles(cls, pattern, samplingRate, checkStack=False,
                           importFrom=ProtImportParticles.IMPORT_FROM_FILES):
        """ Run an Import particles protocol. """
        if importFrom == ProtImportParticles.IMPORT_FROM_SCIPION:
            objLabel = 'from scipion (particles)'
        elif importFrom == ProtImportParticles.IMPORT_FROM_FILES:
            objLabel = 'from file (particles)'

        protImportPart = cls.newProtocol(ProtImportParticles,
                                         objLabel=objLabel,
                                         filesPath=pattern,
                                         sqliteFile=pattern,
                                         samplingRate=samplingRate,
                                         checkStack=checkStack,
                                         importFrom=importFrom)

        cls.launchProtocol(protImportPart)
        # Check that input images have been imported (a better way to do this?)
        if protImportPart.outputParticles is None:
            raise Exception('Import of images: %s, failed. '
                            'outputParticles is None.' % pattern)
        return protImportPart

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
        cls.protImportPart = cls.runImportParticleCryoSPARC(cls.partFn2)

    def testCryosparc2D(self):
        def _runCryosparcClassify2D(label=''):
            prot2D = self.newProtocol(ProtCryo2D,
                                      doCTF=False, maskDiameterA=340,
                                      numberOfMpi=4, numberOfThreads=1)

            prot2D.inputParticles.set(self.protImportPart.outputParticles)
            prot2D.numberOfClasses.set(5)
            prot2D.numberOnlineEMIterator.set(40)
            prot2D.setObjLabel(label)
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
        cls.protImportPart = cls.runImportParticleCryoSPARC(cls.partFn2)

    def testCryosparcInitialModel(self):
        def _runCryosparcInitialModel(label=''):
            protInitialModel = self.newProtocol(ProtCryoSparcInitialModel,
                                                numberOfMpi=4, numberOfThreads=1)

            protInitialModel.inputParticles.set(self.protImportPart.outputParticles)
            protInitialModel.abinit_K.set(1)
            protInitialModel.symmetryGroup.set(SYM_CYCLIC)
            protInitialModel.symmetryOrder.set(1)
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


class TestCryosparc3DRefinement(TestCryosparcBase):

    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        setupTestProject(cls)
        dataProject = 'grigorieff'
        dataset = DataSet.getDataSet(dataProject)
        TestCryosparcBase.setData()
        particlesPattern = dataset.getFile('particles.sqlite')
        cls.protImportPart = cls.runImportParticleCryoSPARC(cls.partFn2)
        cls.protImportVol = cls.runImportVolumesCryoSPARC(cls.volFn)

    def testCryosparc3DRefinement(self):
        def _runCryosparctest3DRefinement(label=''):
            prot3DRefinement = self.newProtocol(ProtCryoSparcRefine3D,
                                                numberOfMpi=4, numberOfThreads=1)

            prot3DRefinement.inputParticles.set(self.protImportPart.outputParticles)
            prot3DRefinement.referenceVolume.set(self.protImportVol.outputVolume)
            prot3DRefinement.symmetryGroup.set(SYM_CYCLIC)
            prot3DRefinement.symmetryOrder.set(1)
            prot3DRefinement.setObjLabel(label)
            self.launchProtocol(prot3DRefinement)
            return prot3DRefinement

        def _checkAsserts(cryosparcProt):
            self.assertIsNotNone(cryosparcProt.outputVolume,
                                 "There was a problem with Cryosparc 3D refinement")
            self.assertEqual(cryosparcProt.outputVolume.getSamplingRate(), 4,
                             'Wrong sampling rate conversion for refined volume')

        cryosparcProtGpu = _runCryosparctest3DRefinement(label="Cryosparc 3D refinement")
        _checkAsserts(cryosparcProtGpu)


class TestCryosparcNonUniformRefine3D(TestCryosparcBase):

    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        setupTestProject(cls)
        dataProject = 'grigorieff'
        dataset = DataSet.getDataSet(dataProject)
        TestCryosparcBase.setData()
        particlesPattern = dataset.getFile('particles.sqlite')
        cls.protImportPart = cls.runImportParticleCryoSPARC(cls.partFn2)
        cls.protImportVolumeVol = cls.runImportVolumesCryoSPARC(cls.volFn)

    def testCryosparcNonUniformRefine3D(self):
        def _runCryosparctestNonUniformRefine3D(label=''):
            protNonUniform3DRefinement = self.newProtocol(ProtCryoSparcNonUniformRefine3D,
                                                          numberOfMpi=4, numberOfThreads=1)



            protNonUniform3DRefinement.inputParticles.set(self.protImportPart.outputParticles)
            protNonUniform3DRefinement.referenceVolume.set(self.protImportVolumeVol.outputVolume)
            protNonUniform3DRefinement.symmetryGroup.set(SYM_CYCLIC)
            protNonUniform3DRefinement.symmetryOrder.set(1)
            protNonUniform3DRefinement.setObjLabel(label)
            self.launchProtocol(protNonUniform3DRefinement)
            return protNonUniform3DRefinement

        def _checkAsserts(cryosparcProt):
            self.assertIsNotNone(cryosparcProt.outputVolume,
                                 "There was a problem with Cryosparc Non-Uniform 3D refinement")

        cryosparcProtGpu = _runCryosparctestNonUniformRefine3D(label="Cryosparc Non-Uniform 3D refinement")
        _checkAsserts(cryosparcProtGpu)


class TestCryosparcParticlesSubtract(TestCryosparcBase):

    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        setupTestProject(cls)
        dataProject = 'grigorieff'
        dataset = DataSet.getDataSet(dataProject)
        TestCryosparcBase.setData()
        particlesPattern = dataset.getFile('particles.sqlite')
        cls.protImportPart = cls.runImportParticleCryoSPARC(cls.partFn2)
        cls.protImportVol = cls.runImportVolumesCryoSPARC(cls.volFn)

    def testCryosparcParticlesSubtract(self):
        def _runCryosparctestParticlesSubtract(label=''):

            protParticlesSubtract = self.newProtocol(ProtCryoSparcSubtract,
                                                     numberOfMpi=4,
                                                     numberOfThreads=1)



            prot3DRefinement = self.newProtocol(ProtCryoSparcRefine3D,
                                                numberOfMpi=4,
                                                numberOfThreads=1)
            prot3DRefinement.inputParticles.set(self.protImportPart.outputParticles)
            prot3DRefinement.referenceVolume.set(self.protImportVol.outputVolume)
            prot3DRefinement.symmetryGroup.set(SYM_CYCLIC)
            prot3DRefinement.symmetryOrder.set(1)
            self.launchProtocol(prot3DRefinement)

            # Create a 3D Mask using xmipp
            xmippProtocols = Domain.importFromPlugin('xmipp3.protocols',
                                                     doRaise=True)
            protXmippCreate3DMask = self.newProtocol(
                xmippProtocols.XmippProtCreateMask3D, source=0)
            protXmippCreate3DMask.inputVolume.set(prot3DRefinement.outputVolume)
            protXmippCreate3DMask.setObjLabel('xmipp: create 3d mask')
            self.launchProtocol(protXmippCreate3DMask)

            protParticlesSubtract.inputParticles.set(prot3DRefinement.outputParticles)
            protParticlesSubtract.refVolume.set(prot3DRefinement.outputVolume)
            protParticlesSubtract.refMask.set(protXmippCreate3DMask.outputMask)
            self.launchProtocol(protParticlesSubtract)

            return protParticlesSubtract

        def _checkAsserts(cryosparcProt):
            self.assertIsNotNone(cryosparcProt.outputParticles,
                                 "There was a problem with Cryosparc subtract projection")

        cryosparcProtGpu = _runCryosparctestParticlesSubtract(label="Cryosparc Subtract projection")
        _checkAsserts(cryosparcProtGpu)


class TestCryosparcLocalRefine(TestCryosparcBase):

    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        setupTestProject(cls)
        dataProject = 'grigorieff'
        dataset = DataSet.getDataSet(dataProject)
        TestCryosparcBase.setData()
        particlesPattern = dataset.getFile('particles.sqlite')
        cls.protImportPart = cls.runImportParticleCryoSPARC(cls.partFn2)
        cls.protImportVol = cls.runImportVolumesCryoSPARC(cls.volFn)

    def testCryosparcLocalRefine(self):
        def _runCryosparctestLocalRefinet(label=''):

            protLocalRefine = self.newProtocol(ProtCryoSparcLocalRefine,
                                               numberOfMpi=4,
                                               numberOfThreads=1)



            prot3DRefinement = self.newProtocol(ProtCryoSparcRefine3D,
                                                numberOfMpi=4,
                                                numberOfThreads=1)
            prot3DRefinement.inputParticles.set(self.protImportPart.outputParticles)
            prot3DRefinement.referenceVolume.set(self.protImportVol.outputVolume)
            prot3DRefinement.symmetryGroup.set(SYM_CYCLIC)
            prot3DRefinement.symmetryOrder.set(1)
            self.launchProtocol(prot3DRefinement)

            # Create a 3D Mask using xmipp
            xmippProtocols = Domain.importFromPlugin('xmipp3.protocols',
                                                     doRaise=True)
            protXmippCreate3DMask = self.newProtocol(
                xmippProtocols.XmippProtCreateMask3D, source=0)
            protXmippCreate3DMask.inputVolume.set(prot3DRefinement.outputVolume)
            protXmippCreate3DMask.setObjLabel('xmipp: create 3d mask')
            self.launchProtocol(protXmippCreate3DMask)

            protLocalRefine.inputParticles.set(prot3DRefinement.outputParticles)
            protLocalRefine.refVolume.set(prot3DRefinement.outputVolume)
            protLocalRefine.refMask.set(protXmippCreate3DMask.outputMask)
            self.launchProtocol(protLocalRefine)

            return protLocalRefine

        def _checkAsserts(cryosparcProt):
            self.assertIsNotNone(cryosparcProt.outputParticles,
                                 "There was a problem with Cryosparc subtract projection")

        cryosparcProtGpu = _runCryosparctestLocalRefinet(label="Cryosparc Local Refine")
        _checkAsserts(cryosparcProtGpu)


class TestUtils(BaseTest):
    def testSamplingRateConvertion(self):
        sr = calculateNewSamplingRate((2, 2, 2), 4, (4, 4, 4))
        self.assertEqual(sr, 8, "Wrong sampling rate conversion 1")

        sr = calculateNewSamplingRate((2, 2, 2), 1.5, (4, 4, 4))
        self.assertEqual(sr, 3, "Wrong sampling rate conversion 2")

        sr = calculateNewSamplingRate((3, 3, 3), 1.5, (4, 4, 4))
        self.assertEqual(sr, 2, "Wrong sampling rate conversion 3")





