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
import commands
import pyworkflow.utils as pwutils
from cryosparc2 import Plugin
from pyworkflow.em import SCIPION_SYM_NAME, String
from pyworkflow.em.constants import (SYM_CYCLIC, SYM_TETRAHEDRAL,
                                     SYM_OCTAHEDRAL, SYM_I222, SYM_I222r)
from pyworkflow.protocol.params import EnumParam, IntParam, Positive
from cryosparc2.constants import (CS_SYM_NAME, SYM_DIHEDRAL_Y,
                                  CRYOSPARC_USER, CRYO_PROJECTS_DIR, CRYOSPARC_DIR)


STATUS_FAILED = "failed"
STATUS_ABORTED = "aborted"
STATUS_COMPLETED = "completed"
STATUS_KILLED = "killed"
STATUS_RUNNING = "running"
STATUS_QUEUED = "queued"
STATUS_LAUNCHED = "launched"
STATUS_STARTED = "started"

STOP_STATUSES = [STATUS_ABORTED, STATUS_COMPLETED, STATUS_FAILED, STATUS_KILLED]
ACTIVE_STATUSES = [STATUS_QUEUED, STATUS_RUNNING, STATUS_STARTED,
                   STATUS_LAUNCHED]


def getCryosparcDir():
    """
    Get the root directory where cryoSPARC code and dependencies are installed.
    """
    return Plugin.getHome()


def getCryosparcProgram():
    """
    Get the cryosparc program to launch any command
    """
    if getCryosparcDir() is not None:
        return os.path.join(getCryosparcDir(),
                            'cryosparc2_master/bin/cryosparcm cli')
    return None


def cryosparcExist():
    """
    Determine if cryosparc software exist
    """
    msg = []
    if getCryosparcDir() is not None and not os.path.exists(getCryosparcDir()):
       msg.append(('The cryoSPARC software do not exist in %s. Please install it')
                  % str(os.environ[CRYOSPARC_DIR]))
    return msg


def isCryosparcRunning():
    """
    Determine if cryosparc services are running
    """
    msg = []
    status = -1
    if getCryosparcProgram() is not None:
        test_conection_cmd = (getCryosparcProgram() +
                                    ' %stest_connection()%s ' % ("'", "'"))
        test_conection = commands.getstatusoutput(test_conection_cmd)
        status = test_conection[0]

    if status != 0:
        msg = ['Failed to establish a new connection with cryoSPARC. Please, '
               'restart the cryoSPARC services. Run the "%s" program located in '
               'the cryosparc_master/bin folder with "%s" parameter' % ("cryosparcm", "start")]

    return msg


def getCryosparcUser():
    """
    Get the full name of the initial admin account
    """
    return os.environ.get(CRYOSPARC_USER, None)


def getCryosparcProjectsDir():
    """
    Get the path on the worker node to a writable directory
    """
    cryoProject_Dir = Plugin.getVar(CRYO_PROJECTS_DIR)

    if not os.path.exists(cryoProject_Dir):
        os.mkdir(cryoProject_Dir)

    return cryoProject_Dir

def getProjectPath(projectDir):
    """
    Gets all projects of given path .
    projectDir: Folder path to get subfolders.
    returns: Set with all subfolders.
    """
    folderPaths = os.listdir(projectDir)
    return folderPaths


def getJobLog(projectDirName, projectName, job):
    """
    Return the job log
    """
    return os.path.join(getCryosparcProjectsDir(), projectDirName, projectName, job,
                        'job.log')


def createEmptyProject(projectDir, projectTitle):
    """
    create_empty_project(owner_user_id, project_container_dir, title=None,
                            desc=None)
    """

    create_empty_project_cmd = (getCryosparcProgram() +
                                ' %screate_empty_project("%s", "%s", "%s")%s '
                                % ("'", str(getCryosparcUser()),
                                   str(projectDir), str(projectTitle), "'"))

    return commands.getstatusoutput(create_empty_project_cmd)


def createProjectDir(project_container_dir):
    """
    Given a "root" directory, create a project (PXXX) dir if it doesn't already
     exist
    :param project_container_dir: the "root" directory in which to create the
                                  project (PXXX) directory
    :param projectName: the name of the project
    :returns: str - the final path of the new project dir with shell variables
              still in the returned path (the path should be expanded every
              time it is used)
    """
    create_project_dir_cmd = (getCryosparcProgram() +
                             ' %scheck_or_create_project_container_dir("%s")%s '
                             % ("'", project_container_dir, "'"))
    return commands.getstatusoutput(create_project_dir_cmd)


def createEmptyWorkSpace(projectName, workspaceTitle, workspaceComment):
    """
    create_empty_workspace(project_uid, created_by_user_id,
                           created_by_job_uid=None,
                           title=None, desc=None)
    returns the new uid of the workspace that was created
    """
    create_work_space_cmd = (getCryosparcProgram() +
                             ' %screate_empty_workspace("%s", "%s", "%s", "%s", "%s")%s '
                             % ("'", projectName, str(getCryosparcUser()),
                                "None", str(workspaceTitle),
                                str(workspaceComment), "'"))
    return commands.getstatusoutput(create_work_space_cmd)


def doImportParticlesStar(protocol):
    """
    do_import_particles_star(puid, wuid, uuid, abs_star_path,
                             abs_blob_path=None, psize_A=None)
    returns the new uid of the job that was created
    """
    className = "import_particles"
    params = {"particle_meta_path": str(os.path.join(os.getcwd(),
                                        protocol._getFileName('input_particles'))),
              "particle_blob_path": str(os.path.join(os.getcwd(),
                                        protocol._getTmpPath())),
              "psize_A": str(protocol._getInputParticles().getSamplingRate())
              }

    p = enqueueJob(className, protocol.projectName, protocol.workSpaceName,
                        str(params).replace('\'', '"'), '{}', protocol.lane)

    import_particles = String(p[-1].split()[-1])

    while getJobStatus(protocol.projectName.get(),
                       import_particles.get()) not in STOP_STATUSES:
        waitJob(protocol.projectName.get(), import_particles.get())

    if getJobStatus(protocol.projectName.get(),
                    import_particles.get()) != STATUS_COMPLETED:
        raise Exception("An error occurred importing the volume. "
                       "Please, go to cryosPARC software for more "
                       "details.")

    return import_particles


def doImportVolumes(protocol, refVolume, volType, msg):
    """
    :return:
    """
    print(msg)
    className = "import_volumes"
    params = {"volume_blob_path": str(refVolume),
              "volume_out_name": str(volType),
              "volume_psize": str(
                  protocol._getInputParticles().getSamplingRate())}

    v = enqueueJob(className, protocol.projectName, protocol.workSpaceName,
                 str(params).replace('\'', '"'), '{}', protocol.lane)

    importedVolume = String(v[-1].split()[-1])

    while getJobStatus(protocol.projectName.get(),
                       importedVolume.get()) not in STOP_STATUSES:
        waitJob(protocol.projectName.get(), importedVolume.get())

    if getJobStatus(protocol.projectName.get(),
                    importedVolume.get()) != STATUS_COMPLETED:
        raise Exception("An error occurred importing the volume. "
                       "Please, go to cryosPARC software for more "
                       "details.")

    return importedVolume


def doJob(jobType, projectName, workSpaceName, params, input_group_conect):
    """
    do_job(job_type, puid='P1', wuid='W1', uuid='devuser', params={},
           input_group_connects={})
    """
    do_job_cmd = (getCryosparcProgram() +
                  ' %sdo_job("%s","%s","%s", "%s", %s, %s)%s' %
                  ("'", jobType, projectName, workSpaceName, getCryosparcUser(),
                   params, input_group_conect, "'"))

    print(pwutils.greenStr(do_job_cmd))
    return commands.getstatusoutput(do_job_cmd)


def enqueueJob(jobType, projectName, workSpaceName, params, input_group_conect,
               lane):
    """
    make_job(job_type, project_uid, workspace_uid, user_id,
             created_by_job_uid=None, params={}, input_group_connects={})
    """
    make_job_cmd = (getCryosparcProgram() +
                  ' %smake_job("%s","%s","%s", "%s", "None", %s, %s)%s' %
                  ("'", jobType, projectName, workSpaceName, getCryosparcUser(),
                   params, input_group_conect, "'"))

    print(pwutils.greenStr(make_job_cmd))
    make_job = commands.getstatusoutput(make_job_cmd)

    enqueue_job_cmd = (getCryosparcProgram() +
                       ' %senqueue_job("%s","%s","%s")%s' %
                       ("'", projectName, String(make_job[-1].split()[-1]),
                        lane, "'"))

    print(pwutils.greenStr(enqueue_job_cmd))
    commands.getstatusoutput(enqueue_job_cmd)
    return make_job


def getJobStatus(projectName, job):
    """
    Return the job status
    """
    get_job_status_cmd = (getCryosparcProgram() +
                          ' %sget_job_status("%s", "%s")%s'
                          % ("'", projectName, job, "'"))

    status = commands.getstatusoutput(get_job_status_cmd)
    return status[-1].split()[-1]


def waitJob(projectName, job):
    """
    Wait while the job not finished
    """
    wait_job_cmd = (getCryosparcProgram() +
                    ' %swait_job_complete("%s", "%s")%s'
                    % ("'", projectName, job, "'"))
    commands.getstatusoutput(wait_job_cmd)


def get_job_streamlog(projectName, job, fileName):

    get_job_streamlog_cmd = (getCryosparcProgram() +
                             ' %sget_job_streamlog("%s", "%s")%s%s'
                             % ("'", projectName, job, "'", ">" + fileName))

    commands.getstatusoutput(get_job_streamlog_cmd)


def killJob(projectName, job):
    """
     Kill a Job (if running)
    :param projectName: the uid of the project that contains the job to kill
    :param job: the uid of the job to kill
    """
    kill_job_cmd = (getCryosparcProgram() +
                    ' %skill_job("%s", "%s")%s'
                    % ("'", projectName, job, "'"))
    print(pwutils.greenStr(kill_job_cmd))
    commands.getstatusoutput(kill_job_cmd)


def clearJob(projectName, job):
    """
         Clear a Job (if queued) to get it back to builing state (do not clear
         params or inputs)
        :param projectName: the uid of the project that contains the job to clear
        :param job: the uid of the job to clear
        ** IMPORTANT: This method can be launch only if the job is queued
        """
    clear_job_cmd = (getCryosparcProgram() +
                    ' %sclear_job("%s", "%s")%s'
                    % ("'", projectName, job, "'"))
    print(pwutils.greenStr(clear_job_cmd))
    commands.getstatusoutput(clear_job_cmd)


def getSystemInfo():
    """
    Get the cryoSPARC system information
    """
    system_info_cmd = (getCryosparcProgram() + ' %sget_system_info()%s') % ("'", "'")
    return commands.getstatusoutput(system_info_cmd)


def addSymmetryParam(form):
    """
    Add the symmetry param with the conventions
    :param form:
    :return:
    """
    form.addParam('symmetryGroup', EnumParam,
                  choices=[CS_SYM_NAME[SYM_CYCLIC] +
                           " (" + SCIPION_SYM_NAME[SYM_CYCLIC] + ")",
                           CS_SYM_NAME[SYM_DIHEDRAL_Y] +
                           " (" + SCIPION_SYM_NAME[SYM_DIHEDRAL_Y] + ")",
                           CS_SYM_NAME[SYM_TETRAHEDRAL] +
                           " (" + SCIPION_SYM_NAME[SYM_TETRAHEDRAL] + ")",
                           CS_SYM_NAME[SYM_OCTAHEDRAL] +
                           " (" + SCIPION_SYM_NAME[SYM_OCTAHEDRAL] + ")",
                           CS_SYM_NAME[SYM_I222] +
                           " (" + SCIPION_SYM_NAME[SYM_I222] + ")",
                           CS_SYM_NAME[SYM_I222r] +
                           " (" + SCIPION_SYM_NAME[SYM_I222r] + ")"],
                  default=SYM_CYCLIC,
                  label="Symmetry",
                  help="Symmetry as defined by cryosparc. Please note that "
                       "Dihedral symmetry in cryosparc is defined with respect"
                       "to y axis (Dyn).\n"
                       "If no symmetry is present, use C1. Enforcing symmetry "
                       "above C1 is not recommended for ab-initio reconstruction"
                  )
    form.addParam('symmetryOrder', IntParam, default=1,
                  condition='symmetryGroup==%d or symmetryGroup==%d' %
                            (SYM_DIHEDRAL_Y-11, SYM_CYCLIC),
                  label='Symmetry Order',
                  validators=[Positive],
                  help='Order of cyclic symmetry.')


def getSymmetry(symmetryGroup, symmetryOrder):
    """
    Get the symmetry(string) taking into account the symmetry convention
    """
    symmetry = {
        0: CS_SYM_NAME[SYM_CYCLIC][0] + str(symmetryOrder),  # Cn
        1: CS_SYM_NAME[SYM_DIHEDRAL_Y][0] + str(symmetryOrder),  #Dn
        2: CS_SYM_NAME[SYM_TETRAHEDRAL],  # T
        3: CS_SYM_NAME[SYM_OCTAHEDRAL],  # O
        4: CS_SYM_NAME[SYM_I222],  # I1
        5: CS_SYM_NAME[SYM_I222r]  # I2
    }
    return symmetry.get(symmetryGroup, "C1")


def calculateNewSamplingRate(newDims, previousSR, previousDims):
    """
    :param newDims:
    :param previousSR:
    :param previousDims:
    :return:
    """
    pX = previousDims[0]
    nX = newDims[0]
    return previousSR*pX/nX


def scaleSpline(inputFn, outputFn, Xdim, Ydim):
    """ Scale an image using splines. """
    # TODO: Avoid using xmipp program for this

    program = "xmipp_image_resize"
    args = "-i %s -o %s --dim %d %d --interp spline" % (inputFn, outputFn, Xdim,
                                                        Ydim)
    xmipp3 = pwutils.importFromPlugin('xmipp3', doRaise=True)
    xmipp3.Plugin.runXmippProgram(program, args)
