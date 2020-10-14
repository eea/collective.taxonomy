from BTrees.OOBTree import OOBTree
from collective.taxonomy import PATH_SEPARATOR
from collective.taxonomy.interfaces import ITaxonomy
from zope.component import (adapter, getMultiAdapter, getUtilitiesFor,
                            queryUtility)
from zope.interface import Interface, implementer
from zope.publisher.interfaces import IPublishTraverse

from plone.api import portal
from plone.restapi.controlpanels.interfaces import IControlpanel
from plone.restapi.deserializer import json_body
from plone.restapi.interfaces import ISerializeToJson
from plone.restapi.services import Service


@implementer(IControlpanel)
class TaxonomyControlPanel(object):
    schema = Interface
    configlet_id = "taxonomy"
    configlet_category_id = "plone-content"
    title = "Taxonomy settings"
    group = ""
    schema = Interface


@implementer(ISerializeToJson)
@adapter(ITaxonomy, Interface)
class TaxonomySerializer(object):
    """
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, full_objects=False):
        site = portal.get()
        util = self.context
        results = {
            '@id': '{}/@taxonomy-data/{}'.format(site.absolute_url(),
                                                 util.name),
            'name': util.name,
            'title': util.title,
            'count': dict(util.count),
        }

        if full_objects:
            results['data'] = {}
            results['order'] = {}
            for (lang, langdata) in util.data.items():
                # keys = [langdata.keys()[x] for x in order]
                results['data'][lang] = [
                    {
                        # TODO: do subpaths
                        'title': k.replace(PATH_SEPARATOR, ''),
                        'token': langdata[k]
                    } for k in langdata.keys()
                ]
                order = util.order[lang]
                results['order'][lang] = list(order)

        return results


@implementer(IPublishTraverse)
class TaxonomyGet(Service):
    """ Taxonomy get service
    """
    taxonomy_id = None

    def publishTraverse(self, request, name):  # noqa
        if name:
            self.taxonomy_id = name

        return self

    def reply(self):
        if self.taxonomy_id:
            return self.reply_taxonomy()

        utils = list(getUtilitiesFor(ITaxonomy))

        res = {
            '@id': self.context.absolute_url() + '/@taxonomy-data',
            'items': [getMultiAdapter((util, self.request),
                                      ISerializeToJson)(full_objects=True)
                      for (name, util) in utils],
        }
        return res

    def reply_taxonomy(self):
        util = queryUtility(ITaxonomy, name=self.taxonomy_id)
        if util is None:
            self.request.response.setStatus(404)
            return

        serializer = getMultiAdapter((util, self.request),
                                     ISerializeToJson)
        return serializer(full_objects=True)


@implementer(IPublishTraverse)
class TaxonomyPatch(Service):
    """ Patch a taxonomy
    """

    taxonomy_id = None

    def publishTraverse(self, request, name):  # noqa
        if name:
            self.taxonomy_id = name

        return self

    def reply(self):
        if not self.taxonomy_id:
            raise Exception("No taxonomy name provided")

        data = json_body(self.request)

        name = data.get('name')

        if name is None:
            raise Exception("No taxonomy name provided")

        taxonomy = queryUtility(ITaxonomy, name=name)
        if taxonomy is None:
            raise Exception("No taxonomy found for this name: {}".format(name))

        for language in data['data'].keys():
            tree = data["data"][language]
            order = data['order'][language]
            if language not in taxonomy.data:
                taxonomy.data[language] = OOBTree()

            data_for_taxonomy = []
            for i in order:
                item = tree[i]
                data_for_taxonomy.append(["{}{}".format(
                    PATH_SEPARATOR, item['title'],
                ), item['token']])

            taxonomy.update(language, data_for_taxonomy, True)

        serializer = getMultiAdapter((taxonomy, self.request),
                                     ISerializeToJson)
        res = serializer(full_objects=True)

        # from pprint import pprint
        # pprint(res)

        return res
