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
import os

import pwem.protocols as pw
import pyworkflow.object as pwobj
import pyworkflow.utils as pwutils

from ..convert import convertBinaryVol, writeSetOfParticles, ImageHandler
from ..utils import (getProjectPath, createEmptyProject,
                     createEmptyWorkSpace, getProjectName,
                     getCryosparcProjectsDir, createProjectDir,
                     doImportParticlesStar, doImportVolumes, killJob, clearJob)


class ProtCryosparcBase(pw.EMProtocol):
    """
    This class contains the common functions for all Cryosparc protocols.
    """

    def _initializeCryosparcProject(self):
        """
        Initialize the cryoSPARC project and workspace
        """
        self._initializeUtilsVariables()
        # create empty project or load an exists one
        folderPaths = getProjectPath(self.projectPath)
        if not folderPaths:
            self.a = createEmptyProject(self.projectPath, self.projectDirName)
            self.projectName = self.a[-1].split()[-1]
        else:
            self.projectName = str(folderPaths[0])

        self.projectName = pwobj.String(self.projectName)
        self._store(self)

        # create empty workspace
        self.b = createEmptyWorkSpace(self.projectName, self.getRunName(),
                                      self.getObjComment())
        self.workSpaceName = pwobj.String(self.b[-1].split()[-1])
        self._store(self)

    def _initializeUtilsVariables(self):
        """
        Initialize all utils cryoSPARC variables
        """
        # Create a cryoSPARC project dir
        self.projectDirName = getProjectName(self.getProject().getShortName())
        self.projectPath = pw.pwutils.join(getCryosparcProjectsDir(),
                                        self.projectDirName)
        self.projectDir = createProjectDir(self.projectPath)

    def convertInputStep(self):
        """ Create the input file in STAR format as expected by Relion.
        If the input particles comes from Relion, just link the file.
        """
        imgSet = self._getInputParticles()
        if imgSet is not None:
            # Create links to binary files and write the relion .star file
            writeSetOfParticles(imgSet, self._getFileName('input_particles'),
                                self._getTmpPath())
            self._importParticles()

        volume = self._getInputVolume()
        if volume is not None:
            self._importVolume()

        mask = self._getInputMask()
        if mask is not None:
            self._importMask()
        else:
            self.mask = None

    def _getScaledAveragesFile(self, csAveragesFile, force=False):

        # For the moment this is the best possible result, scaling from 128 to 300 does not render
        # nice results apart that the factor turns to 299x299.
        # But without this the representative subset is wrong.
        # return csAveragesFile

        scaledFile = self._getScaledAveragesFileName(csAveragesFile, force)

        if not os.path.exists(scaledFile):

            inputSize = self._getInputParticles().getDim()[0]
            csSize = ImageHandler().getDimensions(csAveragesFile)[0]

            if csSize == inputSize:
                print("No binning detected: linking averages cs file.", flush=True)
                pwutils.createLink(csAveragesFile, scaledFile)
            else:
                print("Scaling CS averages file to match particle size (%s -> %s)." % (csSize, inputSize), flush=True)
                try:
                    if force:
                        ImageHandler.scaleSplines(csAveragesFile, scaledFile,
                                                  finalDimension=inputSize,
                                                  forceVolume=force)
                    else:

                        ImageHandler.scale2DStack(csAveragesFile, scaledFile,
                                                  finalDimension=inputSize)
                except Exception as ex:
                    print("The CS averages could not be scaled. %s " % ex)
                    return csAveragesFile

        return scaledFile

    def _getScaledAveragesFileName(self, csAveragesFile, isVolume=False):

        extension = ".mrc" if isVolume else ".mrcs"
        return pwutils.removeExt(csAveragesFile) + "_scaled" + extension

    def _getInputParticles(self):
        return self.inputParticles.get()

    def _getInputVolume(self):
        if self.hasAttribute('refVolume'):
            return self.refVolume.get()
        return None

    def _getInputMask(self):
        if self.hasAttribute('refMask'):
            return self.refMask.get()
        return None

    def _importVolume(self):
        self.vol_fn = os.path.join(os.getcwd(),
                                   convertBinaryVol(
                                       self._getInputVolume(),
                                       self._getTmpPath()))
        self.importVolume = doImportVolumes(self, self.vol_fn, 'map',
                                            'Importing volume...')
        self.currenJob.set(self.importVolume.get())
        self._store(self)

    def _importMask(self):
        self.maskFn = os.path.join(os.getcwd(),
                                   convertBinaryVol(
                                       self._getInputMask(),
                                       self._getTmpPath()))

        self.importMask = doImportVolumes(self, self.maskFn, 'mask',
                                          'Importing mask... ')
        self.currenJob.set(self.importMask.get())
        self._store(self)
        self.mask = self.importMask.get() + '.imported_mask.mask'

    def _importParticles(self):

        # import_particles_star
        self.importedParticles = doImportParticlesStar(self)
        self.currenJob = pwobj.String(self.importedParticles.get())
        self._store(self)

        self.currenJob = pwobj.String(self.importedParticles.get())
        self._store(self)
        self.par = pwobj.String(self.importedParticles.get() + '.imported_particles')

    def setAborted(self):
        """ Set the status to aborted and updated the endTime. """
        pw.EMProtocol.setAborted(self)
        killJob(str(self.projectName.get()), str(self.currenJob.get()))
        clearJob(str(self.projectName.get()), str(self.currenJob.get()))
