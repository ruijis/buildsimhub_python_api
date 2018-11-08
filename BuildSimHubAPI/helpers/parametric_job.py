import time
from .httpurllib import request_get
from .httpurllib import request_post
from .parametric_model import ParametricModel
from .compat import is_py2


class ParametricJob(object):
    # every call will connect to this base URL
    BASE_URL = 'https://my.buildsim.io/'

    def __init__(self, project_api_key, model_api_key='', base_url=None, logger=None):
        """
        Construct a parametric job

        Specify EEM and do parametrics

        :param project_api_key: required
        :param model_api_key: optional
        :param base_url: optional - use for testing only
        :type project_api_key: str
        :type model_api_key: str
        :type base_url: str
        """
        self._project_key = project_api_key
        self._model_api_key = model_api_key
        self._track_token = ""
        self._track_status = ""
        # list of data
        self._model_action_list = list()
        self._base_url = ParametricJob.BASE_URL
        self._logger = None

        if base_url is not None:
            self._base_url = base_url
        if logger is not None:
            self._logger = logger

    @property
    def track_token(self):
        return self._track_token

    @property
    def track_status(self):
        """Get the tracking status"""
        return self._track_status

    @property
    def model_api_key(self):
        return self._model_api_key

    @property
    def project_key(self):
        return self._project_key

    @track_token.setter
    def track_token(self, track_token):
        self._track_token = track_token

    def add_model_measures(self, measures):
        """
        Add measures
        :param measures: list of measures
        :type measures: list of ModelAction
        """
        for measure in measures:
            self._model_action_list.append(measure)

    def add_model_measure(self, measure):
        """
        Add a measure
        :param measure: a measure
        :type measure: ModelAction
        """
        self._model_action_list.append(measure)

    def num_total_combination(self):
        """Number of combinations based on the number of EEM & number of options for each EEM,
            this function serves as a quick check when adding measures to the model
        """
        num_total = 0
        for i in range(len(self._model_action_list)):
            if num_total == 0:
                num_total = self._model_action_list[i].get_num_value()
            else:
                num_total = num_total * self._model_action_list[i].get_num_value()
        return num_total

    def submit_parametric_study_local(self, file_dir, epw_dir=None, unit='ip', simulation_type="parametric",
                                      track=False, request_time=5, customize='false', design_condition='yes',
                                      algorithm='Default', size=200, comment=None):
        """
        Submit an energy model from local as the seed model to a project for this parametric study
        Example:
            project_api_key = "xxx"
            file_dir = "in.idf"

            new_sj = buildsimhub.new_parametric_job(project_api_key)
            new_sj.submit_parametric_study_local(file_dir, track=True)

        :param file_dir:
        :param epw_dir:
        :param unit:
        :param simulation_type: deprecated
        :param track:
        :param request_time:
        :param customize: keep it false if you are not a vendor / enterprise user
        :param algorithm: select algorithms to do the parametric, currently available: 'montecarlo'
        :param size: determine the size of the parametric study - does not work on the Default algorithm
        :param comment: the parametric study description
        :param design_condition: yes or no
        :type file_dir: str
        :type epw_dir: str
        :type unit: str (ip or si)
        :type simulation_type: str
        :type track: bool
        :type request_time: float
        :type customize: str
        :type algorithm: str
        :type size: int
        :type comment: str
        :return: True success, False otherwise
        """
        # file_dir indicates the seed model
        url = self._base_url + 'ParametricSettingUploadModel_API'
        payload = {
            'project_api_key': self._project_key,
            'simulation_type': simulation_type,
            'agents': 1,
            'unit': unit,
            'customize': customize,
            'algorithm': algorithm,
            'size': size,
            'design_cond': design_condition
        }

        if comment is not None:
            # this will override the model description
            payload['comment'] = comment

        for i in range(len(self._model_action_list)):
            action = self._model_action_list[i]
            if algorithm == 'montecarlo':
                data_str = action.get_boundary_string()
                if data_str == "":
                    return
            else:
                data_str = action.get_datalist_string()
                if data_str == "":
                    return

            # client specific requested measures
            if customize == 'true' and data_str == '[]':
                data_str = 'default'
            # payload[action.get_api_name()] = data_str

            # User defined measures
            if action.get_api_name() == 'user_defined':
                if payload.get(action.get_api_name()) is None:
                    payload[action.get_api_name()] = []
                payload[action.get_api_name()].append(data_str)
            else:
                payload[action.get_api_name()] = data_str

            # design customized template
            design_template = action.get_design_template()
            if len(design_template) > 0:
                if payload.get("custom_template") is None:
                    payload["custom_template"] = []
                payload["custom_template"].extend(design_template)

        # Upload files
        files = dict()
        if is_py2:
            files['model'] = open(file_dir, 'r')
            if epw_dir is not None:
                files['weather_file'] = open(epw_dir, 'r')
        else:
            # py3 cannot decode incompatible utf-8 string
            files['model'] = open(file_dir, 'r', errors='ignore')
            if epw_dir is not None:
                files['weather_file'] = open(epw_dir, 'r', errors='ignore')

        print('Submitting parametric simulation job request...')
        r = request_post(url, params=payload, files=files)
        if r.status_code == 500:
            print('Code: ' + str(r.status_code))
            return False
        resp_json = r.json()
        if r.status_code > 200:
            try:
                print('Code: ' + str(r.status_code) + ' message: ' + resp_json['error_msg'])
            except TypeError:
                print(resp_json)
            return False

        print('Received server response')
        if resp_json['status'] == 'success':
            self._track_token = resp_json['tracking']

            # log
            if self._logger is not None:
                self._logger.write_in_message('ParametricSimulation', 'UploadRun', self._project_key,
                                              self._track_token, '200', self._track_token)

            print('You can track the parametric using API key: ' + self._track_token)
            if track:
                while self.track_simulation():
                    print(self._track_status)
                    time.sleep(request_time)
                print(self._track_status)
                print('Completed! You can retrieve results using the key: '+self._track_token)
                res = ParametricModel(self._project_key, self._track_token, self._base_url)
                return res
            else:
                return True
        else:
            print(resp_json['error_msg'])
            return False

    def submit_parametric_study(self, unit='ip', simulation_type='parametric', model_api_key=None,
                                design_condition="yes", track=False, request_time=5, customize='false',
                                algorithm='Default', size=200, comment=None):
        """
        Select a model in the project as the seed model and do parametric study

        Example:
            project_api_key = "xx"
            model_api_key = "xx"

            new_pj = bsh.new_parametric_job(project_api_key, model_api_key)
            new_pj.submit_parametric_study(track=True)

        When model key is empty, you must use submit_parametric_study_local method to upload the seed model
        instead this method

        :param unit:
        :param model_api_key: optional
        :param simulation_type: deprecated
        :param track:
        :param request_time:
        :param customize: keep it false if you are not a vendor / enterprise user
        :param algorithm: select algorithms to do the parametric, currently available: 'montecarlo'
        :param size: determine the size of the parametric study - does not work on the Default algorithm
        :param comment: the parametric study description
        :param design_condition: yes or no
        :type unit: str
        :type model_api_key: str
        :type simulation_type: str
        :type track: bool
        :type request_time: float
        :type customize: str
        :type algorithm: str
        :type size: int
        :type comment: str
        :return: True if success, False otherwise
        """
        if model_api_key is not None:
            self._model_api_key = model_api_key

        if self._model_api_key == '':
            print('submit_parametric_study requires a valid model_api_key')
            return False

        url = self._base_url + 'ParametricSettingCopyModel_API'
        payload = {
            'project_api_key': self._project_key,
            'model_api_key': self._model_api_key,
            'simulation_type': simulation_type,
            'agents': 1,
            'unit': unit,
            'customize': customize,
            'algorithm': algorithm,
            'design_cond': design_condition,
            'size': size
        }

        if comment is not None:
            # this will override the model description
            payload['comment'] = comment

        for i in range(len(self._model_action_list)):
            action = self._model_action_list[i]

            if algorithm == 'montecarlo':
                data_str = action.get_boundary_string()
                if data_str == "":
                    # error processing measures
                    return
            else:
                data_str = action.get_datalist_string()
                if data_str == "":
                    # error processing measures
                    return

            if customize == 'true' and data_str == '[]':
                data_str = 'default'

            if action.get_api_name() == 'user_defined':
                if payload.get(action.get_api_name()) is None:
                    payload[action.get_api_name()] = []
                payload[action.get_api_name()].append(data_str)
            else:
                payload[action.get_api_name()] = data_str

            # design customized template
            design_template = action.get_design_template()
            if len(design_template) > 0:
                if payload.get("custom_template") is None:
                    payload["custom_template"] = []
                payload["custom_template"].extend(design_template)

        print('Submitting parametric simulation job request...')
        r = request_post(url, params=payload)
        if r.status_code == 500:
            print('Code: ' + str(r.status_code))
            return False
        resp_json = r.json()
        if r.status_code > 200:
            try:
                print('Code: ' + str(r.status_code) + ' message: ' + resp_json['error_msg'])
            except TypeError:
                print(resp_json)
            return False
        print('Received server response')

        if resp_json['status'] == 'success':
            self._track_token = resp_json['tracking']

            # log
            if self._logger is not None:
                self._logger.write_in_message('ParametricSimulation', 'Run', self._project_key,
                                              self._track_token, '200', self._track_token)

            print('You can track the parametric using API key: ' + self._track_token)
            if track:
                while self.track_simulation():
                    print(self._track_status)
                    time.sleep(request_time)
                print(self._track_status)
                print('Completed! You can retrieve results using the key: '+self._track_token)
                res = ParametricModel(self._project_key, self._track_token, self._base_url)
                return res
            else:
                return True
        else:
            print(resp_json['error_msg'])
            return False

    def track_simulation(self):
        if self._track_token == "":
            return self._track_status

        url = self._base_url + 'ParametricTracking_API'
        payload = {
            'project_api_key': self._project_key,
            'folder_api_key': self._track_token
        }

        try:
            r = request_get(url, params=payload)
            resp_json = r.json()
        except ConnectionResetError:
            return "Reconnecting to server..."

        if r.status_code > 200:
            try:
                print('Code: ' + str(r.status_code) + ' message: ' + resp_json['error_msg'])
            except TypeError:
                print(resp_json)
            return False

        if 'error_msg' in resp_json:
            self._track_status = resp_json['error_msg']
            return False

        if 'success' in resp_json:

            success = float(resp_json['success'])
            running = float(resp_json['running'])
            error = float(resp_json['error'])
            queue = float(resp_json['queue'])

            divider = success + running + error + queue
            if divider == 0:
                total_progress = 1
            else:
                total_progress = (success + error) / divider

            message = "Total progress %d%%, success: %d, failure: %d, running: %d, queue: %d"
            self._track_status = message % (total_progress * 100, success, error, running, queue)

            if total_progress == 1:
                return False
            else:
                return True
        else:
            print(resp_json['message'])
            return True
