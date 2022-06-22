# -*- coding: utf-8 -*-

from .bklog import BKLogger, getLogger
from .input import ParseParams
from .output import SetOutput
from .const import Status, OutputTemplateType, OutputFieldType, OutputReportType, OutputErrorType

log = BKLogger()
parseParamsObj = ParseParams()
params = parseParamsObj.get_input()
status = Status()
output_template_type = OutputTemplateType()
output_field_type = OutputFieldType()
output_report_type = OutputReportType()
output_error_type = OutputErrorType()


def get_input():
    """
    @summary: 获取 插件输入参数
    @return dict
    """
    return params


def get_project_name():
    """
    @summary: 获取项目英文名
    """
    return params.get("project.name", None)


def get_project_name_cn():
    """
    @summary: 获取项目中文名
    """
    return params.get("project.name.chinese", None)


def get_pipeline_id():
    """
    @summary: 获取流水线ID
    """
    return params.get("pipeline.id", None)


def get_pipeline_name():
    """
    @summary: 获取流水线名称
    """
    return params.get("pipeline.name", None)


def get_pipeline_build_id():
    """
    @summary: 获取buildId
    """
    return params.get("pipeline.build.id", None)


def get_pipeline_build_num():
    """
    @summary: 获取buildno
    """
    return params.get("pipeline.build.num", None)


def get_pipeline_start_type():
    """
    @summary: 获取流水线启动类型
    """
    return params.get("pipeline.start.type", None)


def get_pipeline_start_user_id():
    """
    @summary: 获取流水线启动人
    """
    return params.get("pipeline.start.user.id", None)


def get_pipeline_start_user_name():
    """
    @summary: 获取流水线启动人
    """
    return params.get("pipeline.start.user.name", None)


def get_pipeline_creator():
    """
    @summary: 获取流水线创建人
    """
    return params.get("BK_CI_PIPELINE_CREATE_USER", None)


def get_pipeline_modifier():
    """
    @summary: 获取流水线最近修改人
    """
    return params.get("BK_CI_PIPELINE_UPDATE_USER", None)


def get_pipeline_time_start_mills():
    """
    @summary: 获取流水线启动时间
    """
    return params.get("pipeline.time.start", None)


def get_pipeline_version():
    """
    @summary: 获取流水线的版本
    """
    return params.get("pipeline.version", None)


def get_workspace():
    """
    @summary: 获取工作空间
    """
    return params.get("bkWorkspace", None)


def get_test_version_flag():
    """
    @summary: 当前插件是否是测试版本标识
    """
    return params.get("testVersionFlag", None)


def get_sensitive_conf(key):
    """
    @summary: 获取配置数据
    """
    conf_json = params.get("bkSensitiveConfInfo", None)
    if conf_json:
        return conf_json.get(key, None)
    else:
        return None


def set_output(output):
    """
    @summary: 设置输出
    """
    setOutput = SetOutput()
    setOutput.set_output(output)


def get_credential(credential_id):
    from .openapi import OpenApi
    client = OpenApi()
    return client.get_credential(credential_id)


def get_artifact_urls(file_src, file_path, projectId=None, pipelineId=None, buildNo=None):
    """
    @summary:获取构件下载链接
    """
    if projectId and not pipelineId:
        return False, "pipelineId is null"
    if pipelineId and not projectId:
        return False, "projectId is null"
    from .openapi import OpenApi
    client = OpenApi()
    return client.get_artifacts_url(file_src, file_path, project_id=projectId, pipeline_id=pipelineId, build_no=buildNo)


def get_artifacts_properties(file_src, file_path, projectId=None, pipelineId=None, buildNo=None):
    """
    @summary:获取构建元数
    """
    if projectId and not pipelineId:
        return False, "pipelineId is null"
    if pipelineId and not projectId:
        return False, "projectId is null"
    from .openapi import OpenApi
    client = OpenApi()
    return client.get_artifacts_properties(file_src, file_path, project_id=projectId, pipeline_id=pipelineId,
                                           build_no=buildNo)


def download_file(file_src, file_path, file_name=None, projectId=None, pipelineId=None, buildNo=None):
    """
    @summary: 从仓库下载构件到本地
    """
    from .openapi import OpenApi
    client = OpenApi()

    result, download_url_list = get_artifact_urls(file_src, file_path, projectId=projectId, pipelineId=pipelineId,
                                                  buildNo=buildNo)
    if not result:
        return False, download_url_list

    if len(download_url_list) > 1:
        log.error("found multiple files, confused")
        return False, "found multiple files, confused"
    elif len(download_url_list) == 0:
        log.error("can not find file: {}, {}".format(file_src, file_path))
        return False, "can not find file: {}, {}".format(file_src, file_path)

    return client.download_file(download_url_list[0], file_name)


def get_repo_info(identity, identity_type):
    """
    @summary: 获取代码库信息
    """
    from .openapi import OpenApi
    client = OpenApi()
    return client.get_repo_info(identity, identity_type)


def set_properties(file_src, file_path, properties):
    from .openapi import OpenApi
    client = OpenApi()
    if str(file_src) == "PIPELINE":
        file_path = "/" + get_pipeline_id() + "/" + get_pipeline_build_id() + "/" + str(file_path).replace("/", "", 1)
    elif str(file_src) == "CUSTOM_DIR":
        file_path = "/" + str(file_path).replace("/", "", 1)
    return client.set_properties(file_src, file_path, properties)


def get_context_by_name(context_name):
    from .openapi import OpenApi
    client = OpenApi()
    return client.get_context_by_name(context_name)


if __name__ == "__main__":
    pass
