# -*- coding: utf-8 -*-
import os
import traceback
import requests
import requests_toolbelt as rt
from sys import version_info
import json

from . import setting
from .bklog import BKLogger


class OpenApi():
    _log = BKLogger()

    def __init__(self):
        sdk_json = self.get_sdk_json()
        self.gateway = sdk_json.get("gateway", None)
        self.header_auth = {
            setting.AUTH_HEADER_DEVOPS_BUILD_TYPE: sdk_json.get("buildType", None),
            setting.AUTH_HEADER_DEVOPS_PROJECT_ID: sdk_json.get("projectId", None),
            setting.AUTH_HEADER_DEVOPS_AGENT_ID: sdk_json.get("agentId", None),
            setting.AUTH_HEADER_DEVOPS_AGENT_SECRET_KEY: sdk_json.get("secretKey", None),
            setting.AUTH_HEADER_DEVOPS_BUILD_ID: sdk_json.get("buildId", None),
            setting.AUTH_HEADER_DEVOPS_VM_SEQ_ID: sdk_json.get("vmSeqId", None)
        }

        # 保存session增加3次重试
        self.session = requests.Session()
        self.session.trust_env = False
        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        self.session.mount('http://', adapter)

    def get_sdk_json(self):
        """
        @summary：获取sdk配置
        """
        sdk_path = os.path.join(os.environ.get(setting.BK_DATA_DIR, None), setting.BK_SDK_JSON)
        if not os.path.exists(sdk_path):
            self._log.error("[openapi]init error: sdk json do not exist")
            exit(-1)

        with open(sdk_path, 'r') as f_sdk:
            content = f_sdk.read()
        if not content:
            self._log.error("[openapi]init error: sdk json is null")
            exit(-1)

        try:
            sdk_json = json.loads(content)

            check_result, field = self.check_sdk_json(sdk_json)
            if not check_result:
                self._log.error("[openapi]check sdk json field error: {}".format(field))
                exit(-1)

            return sdk_json
        except Exception as _e:  # pylint: disable=broad-except
            self._log.error("[openapi]parse sdk json error, sdk.json is {}".format(content))
            print(traceback.format_exc())
            exit(-1)

    def check_sdk_json(self, src_json):
        """
        @summary：检查sdk配置
        """
        for field in setting.BK_SDK_JSON_FIELDS:
            if not src_json.get(field, None):
                return False, field

        return True, ""

    def generate_url(self, path):
        """
        @summary：组装访问openapi的url
        """
        if self.gateway.startswith("http://") or self.gateway.startswith("https://"):
            return "{}/{}".format(self.gateway, path.lstrip("/"))
        else:
            return "http://{}/{}".format(self.gateway, path.lstrip("/"))

    def process_response(self, res):
        try:
            if res.status_code == 200:
                ret = res.json()
                if ret["status"] != 0:
                    self._log.error("unexpected status: {}, content is {}".format(ret["status"], ret))
                    return False, {}

                return True, ret["data"]
            else:
                msg = res.json().get("message", "")
                if version_info.major == 2:
                    msg = msg.encode("utf-8")
                self._log.error("unexpected status_code: {}, message is {}".format(res.status_code, msg))
                return False, {}
        except Exception as _e:  # pylint: disable=broad-except
            self._log.error(repr(res.text))
            print(traceback.format_exc())
            return False, {}

    def do_get(self, url, params=None, timeout=60):
        # self._log.debug(url)
        if params:
            res = self.session.get(url, headers=self.header_auth, params=params, timeout=timeout)
        else:
            res = self.session.get(url, headers=self.header_auth, timeout=timeout)

        return self.process_response(res)

    def do_post(self, url, header=None, message=None, timeout=120):
        for key, val in header.items():
            self.header_auth[key] = val

        with self.session as session:
            if message:
                res = session.post(url, headers=self.header_auth, data=json.dumps(message), timeout=timeout)
            else:
                res = session.post(url, headers=self.header_auth, timeout=timeout)

            return self.process_response(res)

    def get_credential(self, credential_id):
        """
        @summary：根据凭据ID，获取凭据内容
        """

        path = "/ticket/api/build/credentials/{}/detail".format(credential_id)
        url = self.generate_url(path)
        return self.do_get(url)

    def get_artifacts_url(self, file_src, file_path, project_id=None, pipeline_id=None, build_no=None):
        """
        @summary: 获取已归档构件的下载链接
        @param file_src：构件源 PIPELINE 从本次已归档构件中获取, CUSTOM_DIR 从自定义版本仓库中获取
        @param file_path: 构件的相对路径
        """
        path = "/artifactory/api/build/artifactories/thirdPartyDownloadUrl"
        params = {
            "artifactoryType": file_src,
            "path": file_path,
            "ttl": 3600 * 24
        }
        if project_id:
            params["projectId"] = project_id
        if pipeline_id:
            params["pipelineId"] = pipeline_id
        if project_id and pipeline_id:
            if build_no:
                params["buildNo"] = build_no
            else:
                params["buildNo"] = "-1"  # 最近一次构建
        url = self.generate_url(path)
        # self._log.debug(url)
        # self._log.debug(params)
        result, artifact_url_list = self.do_get(url, params=params)
        return result, artifact_url_list

    def get_artifacts_properties(self, file_src, file_path, project_id=None, pipeline_id=None, build_no=None):
        """
        @summary: 获取已归档构件的元数据
        @param file_src：构件源 PIPELINE 从本次已归档构件中获取, CUSTOM_DIR 从自定义版本仓库中获取
        @param file_path: 构件的相对路径
        """
        path = "/artifactory/api/build/artifactories/getPropertiesByRegex"
        params = {
            "artifactoryType": file_src,
            "path": file_path
        }
        if project_id:
            params["projectId"] = project_id
        if pipeline_id:
            params["pipelineId"] = pipeline_id
        if project_id and pipeline_id:
            if build_no:
                params["buildNo"] = build_no
            else:
                params["buildNo"] = "-1"
        url = self.generate_url(path)
        # self._log.debug(url)
        # self._log.debug(params)
        return self.do_get(url, params=params)

    def download_file(self, file_url, file_name=None):
        """
        @summary: 下载文件到本地
        @param file_url: 下载链接
        @param file_name: 本地储存的文件名，选填
        @ret file_path_local: 下载后存储的本地路径
        """
        res = self.session.get(file_url, headers=self.header_auth, stream=True)

        if res.status_code != 200:
            self._log.error("download file failed, status_code is {}".format(res.status_code))
            return False, res.status_code

        if not file_name:
            file_url_list = file_url.split("?", 1)
            file_name = os.path.basename(file_url_list[0])

        file_path_local = os.path.join(os.getenv(setting.BK_DATA_DIR, '.'), file_name)
        file_path_dir = os.path.dirname(file_path_local)
        if not os.path.exists(file_path_dir):
            os.makedirs(file_path_dir)

        with open(file_path_local, 'wb') as f_file:
            for chunk in res.iter_content(chunk_size=1048576):
                if chunk:
                    f_file.write(chunk)

        return True, file_path_local

    def get_repo_info(self, identity, identity_type):
        """
        @summary：根据代码库别名，获取代码库详细地址
        """
        path = "/repository/api/build/repositories/"
        params = {
            "repositoryId": identity,
            "repositoryType": identity_type
        }
        url = self.generate_url(path)

        return self.do_get(url, params=params)

    def set_properties(self, file_src, file_path, properties):
        """
        @summary: 设置归档文件元数据
        :param file_src：构件源 PIPELINE 从本次已归档构件中获取, CUSTOM_DIR 从自定义版本仓库中获取
        :param file_path: 构件的相对路径
        :param properties: 新设置的元数据，map类型
        """
        path = "artifactory/api/build/artifactories/properties?artifactoryType={}&path={}" \
            .format(file_src, file_path)
        url = self.generate_url(path)

        header = {
            "Content-type": "application/json"
        }

        ret, _msg = self.do_post(url, header, properties)
        return ret

    def get_context_by_name(self, context_name):
        path = "/process/api/build/variable/get_build_context?contextName={}&check=true" \
            .format(context_name)
        url = self.generate_url(path)
        return self.do_get(url)
