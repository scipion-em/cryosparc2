# ***************************************************************************
# * Authors:    Marta Martinez (mmmtnez@cnb.csic.es)
# *             Roberto Marabini (roberto@cnb.csic.es)
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 3 of the License, or
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
# ***************************************************************************/

import os
import glob
from tempfile import NamedTemporaryFile
import pwem.convert as emconv

from pwem.protocols import (ProtImportParticles,
                            ProtImportVolumes)
from pyworkflow.tests import BaseTest, setupTestProject
import numpy as np
from cryosparc2.protocols import (
    ProtCryoSparcHomogeneousReconstruct,
    ProtCryoSparc3DFlexDataPrepare, # should show output particles
    ProtCryoSparc3DFlexMeshPrepare, # pdb mesh volume mask
    ProtCryoSparc3DFlexTraining,
    ProtCryoSparc3DFlexReconstruction)
import tempfile

class TestFlex(BaseTest):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.xmippAvailable = True
        cls.cryoSparcAvailable = True
        cls.sampling = 1.35
        cls.size = 128
        cls.gpuList = '0'

        from pwem import Domain # import here to avoid ImportError
        try:
            cls.xmipp3 = \
                Domain.importFromPlugin('xmipp3', doRaise=True)
        except Exception as e:
            print("xmipp3 not available, cancel test", e)
            cls.xmippAvailable = False
        cls.absTmpPath = os.path.join(
            cls.getOutputPath(), cls.proj.getTmpPath())

    def __runXmippProgram(self, program, args):
        """ Internal shortcut function to launch a Xmipp program.
        If xmipp not available o fails return False, else True"""
        try:
            from pwem import Domain
            xmipp3 = Domain.importFromPlugin('xmipp3', doRaise=True)
            xmipp3.Plugin.runXmippProgram(program, args)
        except ImportError:
            return False
        return True

    @classmethod
    def runCreateMask(cls, pattern, thr):
        """ Create a volume mask. """
        from xmipp3.protocols import XmippProtCreateMask3D

        cls.msk = cls.newProtocol(XmippProtCreateMask3D,
                                  inputVolume=pattern,
                                  volumeOperation=0,  # OPERATION_THRESHOLD,
                                  threshold=thr,
                                  doSmall=False,
                                  smallSize=False,
                                  doBig=False,
                                  doSymmetrize=False,
                                  doMorphological=False,
                                  doInvert=False,
                                  doSmooth=True,
                                  sigmaConvolution=2
                                  )
        cls.launchProtocol(cls.msk)
        return cls.msk

    @classmethod
    def runApplyMask(cls, volume, mask):
        """ Apply a mask to a volume. """
        from xmipp3.protocols import XmippProtMaskVolumes

        protApplyMask = cls.newProtocol(XmippProtMaskVolumes,
                                        inputVolumes=volume,
                                        source=1,  # SOURCE_VOLUME
                                        inputMask=mask
                                        )
        cls.launchProtocol(protApplyMask)
        return protApplyMask

    @classmethod
    def runImportVolume(cls, pattern, samplingRate,
                        importFrom=ProtImportParticles.IMPORT_FROM_FILES):
        """ Run an Import volumes protocol. """
        protImportVol = cls.newProtocol(ProtImportVolumes,
                                        filesPath=pattern,
                                        samplingRate=samplingRate,
                                        copyFiles=True
                                        )
        cls.launchProtocol(protImportVol)
        return protImportVol

    @classmethod
    def runImportParticles(cls, pattern, samplingRate, checkStack=False,
                           importFrom=ProtImportParticles.IMPORT_FROM_FILES):
        """ Import particles protocol. """
        if importFrom == ProtImportParticles.IMPORT_FROM_SCIPION:
            objLabel = 'from scipion (particles)'
        elif importFrom == ProtImportParticles.IMPORT_FROM_FILES:
            objLabel = 'from file (particles)'
        elif importFrom == ProtImportParticles.IMPORT_FROM_XMIPP3:
            objLabel = 'from xmipp3 (particles)'

        protImportPart = cls.newProtocol(ProtImportParticles,
                                         objLabel=objLabel,
                                         filesPath=pattern,  # input files
                                         sqliteFile=pattern,
                                         mdFile=pattern,
                                         samplingRate=samplingRate,
                                         checkStack=checkStack,
                                         importFrom=importFrom,
                                         voltage=300,
                                         sphericalAberration=2,
                                         amplitudeContrast=.1,
                                         copyFiles=True
                                         )
        cls.launchProtocol(protImportPart)
        # Check that input images have been imported (a better way to do this?)
        if protImportPart.outputParticles is None:
            raise Exception('Import of images: %s, failed. '
                            'outputParticles is None.' % pattern)
        return protImportPart

    def getAtomStructFile(self, atomStructID):
        "download pdb file from the database"
        aSH = emconv.AtomicStructHandler()
        atomStructPath = aSH.readFromPDBDatabase(
            atomStructID, dir=self.absTmpPath, type='pdb')
        # filter out HETATM
        tempFile  = os.path.join(self.absTmpPath, "kk")
        os.system(
            f"cat {atomStructPath} |"
            f" grep -v HETATM > {tempfile}; mv {tempfile} {atomStructPath}")
        return atomStructPath

    def createVolume(self, atomStructPath, volMapName):
        # create volume
        volumeName = f"{volMapName}"
        self.__runXmippProgram('xmipp_volume_from_pdb', f'-i {atomStructPath}'
                               f' -o {volumeName} --size {self.size}'
                               f' --centerPDB --sampling {self.sampling}')
        return volumeName + '.vol'

    def shiftFirstChain(
            self,
            atomStructPath,
            translation_vector=[0.0, 0.0, 0.0],
            nTimes=1):
        # impoer PDB needs new version of Biopython
        # orrecent version of pwem
        # leave the import here so it is not executed
        # during the test detection
        from Bio.PDB import PDBParser, PDBIO

        def translate_structure(structure, translation_vector):
            """
            Translate the structure by a given vector.

            Args:
                structure: Biopython structure object.
                translation_vector: List or tuple of (x, y, z)
                                    translation values.
            """
            translation_vector = translation_vector * nTimes
            for model in structure:
                for chain in model:
                    for residue in chain:
                        for atom in residue:
                            # Translate the atom's coordinates
                            new_coord = atom.coord + translation_vector
                            atom.coord = new_coord
                    break  # Break after the first chain
        parser = PDBParser(QUIET=True)
        structure = parser.get_structure("example_structure", atomStructPath)
        translate_structure(structure, translation_vector)
        io = PDBIO()
        io.set_structure(structure)
        output_path = atomStructPath.replace(".ent", f"_shifted_{nTimes}.pdb")
        io.save(output_path)
        return output_path

    def createProjections(self, volumeNames, angular_sampling_rate=15):
        projStackNames = []
        for vol in volumeNames:
            print("Creating projections for volume:",  vol)
            args = " -i %s" % vol
            args += " -o %s" % vol.replace(".vol", ".mrcs")
            args += f" --sampling_rate {angular_sampling_rate}"
            args += " --sym c1"
            args += " --method real_space"
            # args += " --method real_space&"
            progname = "xmipp_angular_project_library"
            self.xmipp3.Plugin.runXmippProgram(progname, args)
            projStackNames.append(vol.replace(".vol", ".doc"))
        # For production remove '&' and sleep
        # import time
        # time.sleep(25)
        return projStackNames

    def createCTFdata(self):
        ctfFileName = os.path.join(self.absTmpPath, "ctf.ctfdata")
        ctfFile = open(ctfFileName, "wb")
        command = f"""# XMIPP_STAR_1 *
#  SamplingRate should be the same that the one used in the micrographs
data_fullMicrograph
 _ctfSamplingRate {self.sampling}
 _ctfVoltage 300
 _ctfDefocusU 6000
 _ctfDefocusV 6000
 _ctfDefocusAngle -140.258
 _ctfSphericalAberration 2
 _ctfQ0 0.1
"""
        ctfFile.write(command.encode('utf8'))
        ctfFile.close()
        return ctfFile.name

    def unionSets(self, xmdProjNames):

        for i in range(1, len(xmdProjNames)):
            args = " -i %s" % xmdProjNames[0]
            args += " --set union %s" % xmdProjNames[i]
            args += " -o %s" % xmdProjNames[0]
            progname = "xmipp_metadata_utilities"
            self.xmipp3.Plugin.runXmippProgram(progname, args)
        return xmdProjNames[0]

    def addNoiseAndCTF(self, projDocNames):
        ctfFile = self.createCTFdata()
        print("ctfFile", ctfFile)
        xmdProjNames = []
        for projDocName in projDocNames:
            args = " -i %s" % projDocName
            args += " -o %s" % projDocName.replace(".doc", "ctf.mrcs")
            args += f" --ctf {ctfFile}"
            args += " --noise 10 --after_ctf_noise"
            progname = "xmipp_phantom_simulate_microscope"
            self.xmipp3.Plugin.runXmippProgram(progname, args)
            xmdProjNames.append(projDocName.replace(".doc", "ctf.xmd"))
        xmdProjName = self.unionSets(xmdProjNames)
        return xmdProjName

    def importData(self, xmdProjName, volName):
        # import particles
        protImportProj = self.runImportParticles(
            xmdProjName,
            self.sampling,
            importFrom=ProtImportParticles.IMPORT_FROM_XMIPP3)
        # import volume
        protImportVolume = self.runImportVolume(
            volName,
            self.sampling)
        return protImportProj, protImportVolume

    def protCryosparcReconstruct(self, particles, mask):
        recProt1 = self.newProtocol(
            ProtCryoSparcHomogeneousReconstruct,
            gpuList=self.gpuList,
            refmask=mask,
            inputParticles=particles)

        protRelionReconstruct = self.launchProtocol(recProt1)
        return protRelionReconstruct

    def runDataPrepare(
            self, particles,volume, trainigBoxSize=128):
        protDataPrepare = self.newProtocol(
            ProtCryoSparc3DFlexDataPrepare,
            refVolume=volume,
            inputParticles=particles,
            bin_size_pix=trainigBoxSize)
        self.launchProtocol(protDataPrepare)
        return protDataPrepare

    def runCryoSparc3DFlexMeshPrepare(self, protDataPrepare, mask):
        protMeshPrepare = self.newProtocol(
            ProtCryoSparc3DFlexMeshPrepare,
            dataPrepare=protDataPrepare,
            refmask=mask,
            gpuList=self.gpuList
            )
        self.launchProtocol(protMeshPrepare)
        return protMeshPrepare

    def runCryoSparc3DFlexTraining(self, protDataPrepare,
                                   protMeshPrepare, flex_K=3):
        protFlexTraining = self.newProtocol(
            ProtCryoSparc3DFlexTraining,
            input3DFlexDataPrepareProt=protDataPrepare,
            input3DMeshFlexPrepareProt=protMeshPrepare,
            flex_K=flex_K,
            gpuList=self.gpuList
            )
        self.launchProtocol(protFlexTraining)
        return protFlexTraining

    def runCryoSparc3DFlexReconstruction(self, prot3DFlexTraining):
        print("runCryoSparc3DFlexReconstruction_1")
        protFlexReconstruction = self.newProtocol(
            ProtCryoSparc3DFlexReconstruction,
            input3DFlexTrainingProt=prot3DFlexTraining,
            gpuList=self.gpuList
            )
        print("runCryoSparc3DFlexReconstruction_2")
        self.launchProtocol(protFlexReconstruction)
        print("runCryoSparc3DFlexReconstruction_3")
        return protFlexReconstruction

    def testFlexSystem(self):
        if not self.xmippAvailable:
            # if xmipp is not available, just
            # skip this test
            return
        atomStructID = '3wtg'
        nVolumes = 3  # realistic value 5
        self.angular_sampling_rate = 10  # realistic value 3
        volMapName = os.path.join(
            self.absTmpPath, f'{atomStructID}_shifted_%d')
        atomStructPath = self.getAtomStructFile(atomStructID)
        translation_vector = np.array([0.5, 0.0, -0.25])
        volumeNames = []

        for i in range(nVolumes):
            shiftChain = self.shiftFirstChain(
                atomStructPath=atomStructPath,
                translation_vector=translation_vector,
                nTimes=i)
            volumeName = self.createVolume(
                atomStructPath=shiftChain,
                volMapName=volMapName % i)
            volumeNames.append(volumeName)
        projDocNames = self.createProjections(
            volumeNames, self.angular_sampling_rate)
        xmdProjFile = self.addNoiseAndCTF(projDocNames)
        volName = volumeNames[0]
        print("import data")
        protImportProj, protImportVolume =\
            self.importData(xmdProjName=xmdProjFile, volName=volName)
        print("create mask")
        protCreateMask = self.runCreateMask(
            pattern=protImportVolume.outputVolume,
            thr=0.1)
        print("reconstruction")
        protCryoSparcReconstruct = \
            self.protCryosparcReconstruct(
                protImportProj.outputParticles,
                protCreateMask.outputMask)
        print("apply mask")
        protApplyMask = self.runApplyMask(
            protCryoSparcReconstruct.outputVolume,
            protCreateMask.outputMask)
        print("data prepare (flex)")
        protFlexDataPrepare = self.runDataPrepare(
            protImportProj.outputParticles,
            protApplyMask.outputVol,
            trainigBoxSize=128,
            )
        print("mesh prepare")
        protCryoSparc3DFlexMeshPrepare = self.runCryoSparc3DFlexMeshPrepare(
            protFlexDataPrepare,
            protApplyMask.outputVol,
        )
        print("training")
        protCryoSparc3DFlexTraining = self.runCryoSparc3DFlexTraining(
            protFlexDataPrepare,
            protCryoSparc3DFlexMeshPrepare,
            flex_K=3,
        )
        print("flex reconstruction")
        protCryoSparc3DFlexReconstruction = self.runCryoSparc3DFlexReconstruction(
            protCryoSparc3DFlexTraining,
        )
