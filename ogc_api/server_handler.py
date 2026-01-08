import io
import json

import s2sphere

from ogc_api import index, geometry
from ogc_api.data_structures import WFSLink, APIResponse, HTTP_RESPONSES

DEFAULT_LIMIT = 10
MAX_LIMIT = 1000
MAX_SIGNATURE_WIDTH = 8.0


class WebServer:
    index: index.Index

    def handle_landing_request(self):
        class LandingPageResponse:
            title: str
            description: str
            links: []

            def to_json(self):
                return dict(title=self.title, description=self.description, links=self.links)

        response = LandingPageResponse()
        response.links = []
        response.title = "OGC API - Features server"
        response.description = "Web API that conforms to the OGC API Features specification."

        landing_link = WFSLink()
        landing_link.href = self.index.public_path
        landing_link.rel = "self"
        landing_link.type = "application/json"
        landing_link.title = "This document"

        response.links.append(landing_link.to_json())

        api_link = WFSLink()

        api_link.href = self.index.public_path + "api"
        api_link.rel = "service-desc"
        api_link.type = "application/openapi+json;version=3.0"
        api_link.title = "The API definition"

        response.links.append(api_link.to_json())

        collections_link = WFSLink()

        collections_link.href = self.index.public_path + "collections"
        collections_link.rel = "data"
        collections_link.type = "application/json"
        collections_link.title = "Metadata about the feature collections"

        response.links.append(collections_link.to_json())

        # collections = self.index.get_collections()

        # for collection in collections:
        #     link = WFSLink()
        #     link.href = self.index.public_path + "collections/" + collection.name
        #     link.rel = "item"
        #     link.type = "application/json"
        #     link.title = "Information about the " + collection.name + " data"
        #
        #     items_link = WFSLink()
        #     items_link.href = self.index.public_path + "collections/" + collection.name + "/items"
        #     items_link.rel = "item"
        #     items_link.type = "application/geo+json"
        #     items_link.title = collection.name + " as GeoJSON"
        #
        #     response.links.append(link.to_json())
        #     response.links.append(items_link.to_json())

        content = json.dumps(response.to_json(), indent=2)

        return APIResponse(content=content, http_response=None)

    def handle_collections_request(self, collection_parameter: str = None):
        collections = []

        if collection_parameter is None:
            collections = self.index.get_collections()
        else:
            response = self.index.get_collection(collection_parameter)
            if response.http_response is not None:
                return APIResponse(None, response.http_response)

            collections.append(response.content)

        wfs_collections = []
        content = None

        class WFSCollection:
            id: str
            title: str
            links: [] = []

            def __init__(self):
                self.links = []
                self.title = ""
                self.id = ""

            def to_json(self):
                return dict(id=self.id, title=self.title, links=self.links)

        class WFSCollectionResponse:
            links: [] = []
            collections: [] = []

            def to_json(self):
                return dict(links=self.links, collections=self.collections)

        for collection in collections:
            link = WFSLink()
            link.href = self.index.public_path + "collections/" + collection.name
            if collection_parameter is not None:
                link.rel = "self"
            else:
                link.rel = "item"
            link.type = "application/json"
            link.title = "Information about the " + collection.name + " data"

            items_link = WFSLink()
            items_link.href = self.index.public_path + "collections/" + collection.name + "/items"
            items_link.rel = "item"
            items_link.type = "application/geo+json"
            items_link.title = collection.name + " as GeoJSON"

            wfs_collection = WFSCollection()
            wfs_collection.id = collection.name
            wfs_collection.title = "A collection of " + collection.name + " features"

            # print(link.to_json())
            # print(items_link.to_json())
            wfs_collection.links.append(link.to_json())
            wfs_collection.links.append(items_link.to_json())

            wfs_collections.append(wfs_collection.to_json())

            if collection_parameter is not None:
                content = wfs_collection

        self_link = WFSLink()
        self_link.href = self.index.public_path + "collections"
        self_link.rel = "self"
        self_link.type = "application/json"
        self_link.title = "Collections"

        result = WFSCollectionResponse()
        result.collections = wfs_collections
        result.links.append(self_link.to_json())

        if content is None:
            content = json.dumps(result.to_json(), indent=2)
        else:
            content = json.dumps(content.to_json(), indent=2)

        return APIResponse(content, None)

    def handle_items_request(self, collection: str, start_id: str, start: int, bbox: str, limit: str):
        response = parse_bbox(bbox)

        if response.http_response is not None:
            return APIResponse(None, response.http_response)

        features = io.BytesIO()
        if type(limit) is not int:
            if limit.isdigit():
                limit = int(limit)
            else:
                return APIResponse(None, HTTP_RESPONSES["BAD_REQUEST"])

        if limit <= 0:
            limit = 1
        elif not (0 < limit <= MAX_LIMIT):
            return APIResponse(None, HTTP_RESPONSES["BAD_REQUEST"])

        include_links = True
        api_response = self.index.get_items(collection, start_id, start, limit, response.content, include_links,
                                            features)
        api_response.content = json_dumps_for_response(api_response.content, without_indent=True)

        return api_response

    def handle_item_request(self, collection: str, feature_id: str):
        api_response = self.index.get_item(collection, feature_id)
        api_response.content = json_dumps_for_response(api_response.content)

        return api_response


def make_web_server(idx: index.Index):
    server = WebServer()
    server.index = idx

    return server


def parse_bbox(bbox_string: str):
    bbox = s2sphere.LatLngRect()
    bbox_string = str.strip(bbox_string)

    if len(bbox_string) == 0:
        return APIResponse(bbox, None)

    edges = str.split(bbox_string, ",")
    float_edges = []

    for edge in edges:
        try:
            float_edges.append(float(str.strip(edge)))
        except ValueError:
            return APIResponse(None, HTTP_RESPONSES["BAD_REQUEST"])

    if len(float_edges) == 4:
        bbox = bbox.from_point_pair(s2sphere.LatLng.from_degrees(float_edges[1], float_edges[0]),
                                    s2sphere.LatLng.from_degrees(float_edges[3], float_edges[2]))

        if bbox.is_valid:
            return APIResponse(bbox, None)

    if len(float_edges) == 6:
        bbox = bbox.from_point_pair(s2sphere.LatLng.from_degrees(float_edges[1], float_edges[0]),
                                    s2sphere.LatLng.from_degrees(float_edges[4], float_edges[3]))

        if bbox.is_valid():
            return APIResponse(bbox, None)

    return APIResponse(s2sphere.LatLngRect(), HTTP_RESPONSES["BAD_REQUEST"])


def format_items_url(path: str, collection: str, start_id: str, start: int, bbox: s2sphere.LatLngRect, limit: int):
    params = []

    if len(start_id) > 0:
        params.append(str.format("start_id={0}", start_id))

    if start > 0:
        params.append(str.format("start={0}", start))

    if not bbox.is_empty():
        bbox_str = geometry.encode_bbox(bbox)
        bbox_params = str.format("bbox={0},{1},{2},{3}", bbox_str[0], bbox_str[1], bbox_str[2], bbox_str[3])
        params.append(bbox_params)

    if limit != DEFAULT_LIMIT:
        params.append(str.format("limit={0}", str(limit)))

    url = str.format("{0}collections/{1}/items", path, collection)

    if len(params) > 0:
        url += "?" + "&".join(params)

    return url


def json_dumps_for_response(data, without_indent=False):
    if without_indent:
        return json.dumps(data,
                          ensure_ascii=False,
                          allow_nan=False,
                          indent=None,
                          separators=(",", ":")
                          ).encode("utf-8")
    else:
        return json.dumps(data,
                          ensure_ascii=False,
                          allow_nan=False,
                          indent=2
                          ).encode("utf-8")
