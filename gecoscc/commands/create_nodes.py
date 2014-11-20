import requests

from optparse import make_option

from bson import ObjectId

from chef import Node as ChefNode
from chef.node import NodeAttributes

from gecoscc.management import BaseCommand
from gecoscc.utils import get_chef_api


class Command(BaseCommand):
    description = """
        Create nodes
    """
    usage = ("usage: %prog create_nodes --number 100000 "
             "--organisational-unit-id 1234567890abcdef12345678 --copy-computer-id 1234567890abcdef12345678 "
             "--gecoscc-url http://localhost --gecoscc-username admin --gecoscc-password admin")

    option_list = [
        make_option(
            '-n', '--number',
            dest='number',
            action='store',
            help='Number of nodes to create'
        ),
        make_option(
            '-o', '--organisational-unit-id',
            dest='ou_id',
            action='store',
            default=False,
            help='Organisational unit id'
        ),
        make_option(
            '-c', '--copy-computer-id',
            dest='comp_id',
            action='store',
            default=False,
            help='Computer id'
        ),
        make_option(
            '-s', '--gecoscc-username',
            dest='gcc_username',
            action='store',
            help='An existing gecoscc administrator username'
        ),
        make_option(
            '-p', '--gecoscc-password',
            dest='gcc_password',
            action='store',
            help='The password of the gecoscc administrator'
        ),
        make_option(
            '-u', '--gecoscc-url',
            dest='gcc_url',
            action='store',
            help='The url where gecoscc is running'
        ),
        make_option(
            '-r', '--prefix',
            dest='prefix',
            action='store',
            help='Prefix',
            default='scheherezade-'
        ),
    ]

    def command(self):
        db = self.pyramid.db
        ou = db.nodes.find_one({'_id': ObjectId(self.options.ou_id)})
        if not ou:
            print 'Error OU does not exists'
            return
        comp = db.nodes.find_one({'_id': ObjectId(self.options.comp_id)})
        if not comp:
            print 'Error computer does not exists'
            return
        node_id = comp.get('node_chef_id', None)
        if not comp:
            print 'Error this computer has not node_chef_id'
            return
        admin = db.adminusers.find_one({'username': self.options.gcc_username})
        if not admin:
            print 'Error this admin does not exists'
            return
        elif not admin.get('is_superuser', None):
            print 'You need a super admin'
            return
        number_nodes = int(self.options.number)
        api = get_chef_api(self.settings,
                           admin)
        node = ChefNode(node_id, api)
        for i in range(number_nodes):
            new_node_name = '%s-%s' % (self.options.prefix, i)
            new_node = ChefNode(new_node_name, api)
            for attr in node.to_dict().keys():
                if hasattr(node, attr) and attr != 'name':
                    if attr == 'automatic':
                        automatic_dict = node.automatic.to_dict()
                        automatic_dict['ohai_gecos']['pclabel'] = new_node_name
                        automatic = NodeAttributes(automatic_dict)
                        setattr(new_node, attr, automatic)
                    else:
                        setattr(new_node, attr, getattr(node, attr))
            new_node.save()
            print 'Created %s at chef' % new_node_name
            res = requests.post('%s/register/computer/' % self.options.gcc_url,
                                {'ou_id': self.options.ou_id, 'node_id': new_node_name},
                                auth=(self.options.gcc_username, self.options.gcc_password))
            if res.ok and res.json()['ok']:
                print 'Created %s at gcc' % new_node_name
            elif res.ok and not res.json()['ok']:
                print 'Error %s at gcc' % new_node_name
                print '\t %s' % res.json()['message']
            else:
                print 'Unknow error %s at gcc' % new_node_name
                