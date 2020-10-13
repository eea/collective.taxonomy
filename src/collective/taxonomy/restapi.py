import json

from collective.taxonomy.interfaces import ITaxonomy
from zope.component import (adapter, getMultiAdapter, getUtilitiesFor,
                            queryUtility)
from zope.interface import Interface, implementer
from zope.publisher.interfaces import IPublishTraverse

from plone.api import portal
from plone.restapi.deserializer import json_body
from plone.restapi.interfaces import ISerializeToJson
from plone.restapi.services import Service

from .jsonimpl import EditTaxonomyData


"""
{'count': {'en': 5},
 'data': {'en': <BTrees.OOBTree.OOBTree object at 0x7f541bd6c680 oid 0x36bb in
 <Connection at 7f541b9eff50>>},
  'default_language': 'en',
   'name': 'collective.taxonomy.nuts_code',
    'order': {'en': <BTrees.IOBTree.IOBTree object at 0x7f54219ae200 oid 0x36bc
    in <Connection at 7f541b9eff50>>},
     'title': 'NUTS Codes',
      'version': {'en': 2}}
"""


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
                    {'title': k, 'token': langdata[k]} for k in langdata.keys()
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


class TaxonomyPost(Service):
    """ Returns the querystring search results given a p.a.querystring data.
    """

    def reply(self):
        data = json_body(self.request)

        name = data.get('name')

        if name is None:
            raise Exception("No index name provided")

        catalog = portal.get_tool(name='portal_catalog')
        values = list(catalog.uniqueValuesFor(name))

        return sorted(values)
