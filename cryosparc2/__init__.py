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
import pwem as em
import pyworkflow.utils as pwutils

from .constants import *

__version__ = '3.3.10'
_references = ['Punjani2017', 'Brubaker2017', 'daniel_asarnow_2019_3576630']
_logo = 'cryosparc2_logo.png'


class Plugin(em.Plugin):
    _url = "https://github.com/scipion-em/scipion-em-cryosparc2"
    _homeVar = CRYOSPARC_HOME
    _pathVars = [CRYOSPARC_HOME]
    _supportedVersions = [V2_5_0, V2_8_0, V2_9_0, V2_11_0, V2_12_0, V2_12_2,
                          V2_12_4, V2_13_0, V2_13_2, V2_14_0, V2_14_2, V2_15_0,
                          V3_0_0, V3_0_1, V3_1_0, V3_2_0, V3_3_0, V3_3_1]

    @classmethod
    def _defineVariables(cls):
        cls._defineVar(CRYOSPARC_HOME, os.environ.get(CRYOSPARC_DIR, ""))
        cls._defineVar(CRYO_PROJECTS_DIR, "scipion_projects")

    @classmethod
    def getEnviron(cls):
        """ Setup the environment variables needed to launch cryoSparc. """
        environ = pwutils.Environ(os.environ)
        environ.update({'PATH': cls.getHome()},
                       position=pwutils.Environ.BEGIN)

        return environ

    @classmethod
    def defineBinaries(cls, env):
        PYEM_VERSION = '22.01.18'  # This is our made up version
        PYEM_INSTALLED = 'pyem-%s_installed' % PYEM_VERSION
        installationCmd = 'pip uninstall -y pyem && pip install git+https://github.com/asarnow/pyem.git@48541ff4e2a62be3a185d0ce9b76c5a37b1da15a'
        installationCmd += ' && touch %s' % PYEM_INSTALLED

        env.addPackage('pyem', commands=[(installationCmd, PYEM_INSTALLED)],
                       version=PYEM_VERSION, tar='void.tgz',
                       createBuildDir=True, buildDir='pyem-%s' % PYEM_VERSION,
                       default=True)
