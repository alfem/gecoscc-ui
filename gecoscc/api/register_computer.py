from bson import ObjectId

from cornice.resource import resource

from pyramid.threadlocal import get_current_registry

from gecoscc.api import BaseAPI
from gecoscc.models import Node as MongoNode
from gecoscc.permissions import http_basic_login_required
from gecoscc.utils import get_chef_api, register_node, apply_policies_to_computer


@resource(path='/register/computer/',
          description='Register computer from chef',
          validators=http_basic_login_required)
class RegisterComputerResource(BaseAPI):

    schema_detail = MongoNode
    collection_name = 'nodes'

    def post(self):
        ou_id = self.request.POST.get('ou_id')
        node_id = self.request.POST.get('node_id')
        ou = None
        if ou_id:
            ou = self.collection.find_one({'_id': ObjectId(ou_id), 'type': 'ou'})
        else:
            ou_availables = self.request.user.get('ou_availables')
            if isinstance(ou_availables, list) and len(ou_availables) > 0:
                ou = self.collection.find_one({'_id': {'$in': [ObjectId(ou_ava_id) for ou_ava_id in ou_availables]},
                                               'type': 'ou',
                                               'path': {'$ne': 'root'}})
        if not ou:
            return {'ok': False,
                    'message': 'Ou does not exists'}

        settings = get_current_registry().settings
        api = get_chef_api(settings, self.request.user)
        computer_id = register_node(api, node_id, ou, self.collection)
        if not computer_id:
            return {'ok': False,
                    'message': 'Node does not exist (in chef)'}
        computer = self.collection.find_one({'_id': computer_id})
        apply_policies_to_computer(self.collection, computer, self.request.user)
        return {'ok': True}

    def put(self):
        node_id = self.request.POST.get('node_id')
        computer = self.collection.find_one({'node_chef_id': node_id})
        if not computer:
            return {'ok': False,
                    'message': 'Computer does not exists'}
        apply_policies_to_computer(self.collection, computer, self.request.user)
        return {'ok': True}

    def delete(self):
        node_id = self.request.GET.get('node_id')
        node_deleted = self.collection.remove({'node_chef_id': node_id, 'type': 'computer'})
        num_node_deleted = node_deleted['n']
        if num_node_deleted == 1:
            return {'ok': True}
        elif num_node_deleted < 1:
            return {'ok': False,
                    'message': 'This node does not exist (mongodb)'}
        elif num_node_deleted > 1:
            return {'ok': False,
                    'message': 'Deleted %s computers' % num_node_deleted}
