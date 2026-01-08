import logging
import os

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

from ogc_api.index import make_index
from ogc_api.server_handler import json_dumps_for_response, DEFAULT_LIMIT
from ogc_api.server_handler import make_web_server

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

COLLECTIONS_ENV = os.environ.get('COLLECTIONS')
PORT_ENV = os.environ.get('PORT')

LOCAL_WEB_URL = "http://127.0.0.1"
DOCKER_WEB_URL = "http://0.0.0.0"

WEB_HOST_URL = str.format('{0}:{1}/', DOCKER_WEB_URL if PORT_ENV else LOCAL_WEB_URL, PORT_ENV if PORT_ENV else '8000')

SHORT_INDEX_MESSAGE = 'This is a mini OGC API server compliant with the ' \
                      '<a href="https://docs.opengeospatial.org/is/17-069r3/17-069r3.html" target="_blank">' \
                      'OGC API - Features</a>.<br/>' \
                      'The server is written in Python ' \
                      '<a href=\"https://gitlab.com/labiangashi/python-wfs-server\" ' \
                      'target="_blank" title="Repository">here</a>' \
                      ', it serves GeoJSON objects and PNG raster tiles. <br />'

INDEX_MESSAGE = f'{SHORT_INDEX_MESSAGE}' \
                '<br/>' \
                '<strong>Available API methods: </strong><br/>' \
                '<ol>' \
                '<strong><i>OGC API Endpoints: </i></strong><br/>' \
                '<li><i>/collections</i></li>' \
                '<li><i>/collections/{collection}</i></li>' \
                '<li><i>/collections/{collection}/items</i></li>' \
                '<li><i>/collections{collection}/items/{feature_id}</i></li>' \
                '</ol>' \
                '<ol>' \
                '<strong><i>Other Endpoints: </i></strong><br/>' \
                '<li><i>/tiles/{collection}/{zoom}/{x}/{y}.png</i></li>' \
                '<li><i>/tiles/{collection}/{zoom}/{x}/{y}/{a}/{b}.geojson</i></li>' \
                '</ol>'


def main():
    collections = {}

    if COLLECTIONS_ENV:
        for collection_object in str.split(COLLECTIONS_ENV, ","):
            value = str.split(collection_object, "=")
            if value is None or len(value) != 2:
                return logging.fatal('Malformed parameters for the --collections argument, '
                                     'pass something like: "COLLECTIONS=castles=path/to/c.geojson,'
                                     'lakes=path/to/l.geojson"')

            collections[value[0]] = value[1]

    idx = make_index(collections, WEB_HOST_URL)
    server = make_web_server(idx)

    @app.get("/")
    def landing_page():
        api_response = server.handle_landing_request()

        return Response(content=api_response.content,
                        headers={
                            "content-type": "application/json",
                            "content-length": str(len(api_response.content))
                        })

    # region OGC API endpoints
    @app.get("/collections")
    def get_collections():
        api_response = server.handle_collections_request()

        return Response(content=api_response.content,
                        headers={
                            "content-type": "application/json",
                            "content-length": str(len(api_response.content))
                        })

    @app.get("/collections/{collection}")
    def get_collection(collection: str):
        api_response = server.handle_collections_request(collection)

        if api_response.http_response is not None:
            return Response(content=None, status_code=api_response.http_response.status_code)

        return Response(content=api_response.content,
                        headers={
                            "content-type": "application/json",
                            "content-length": str(len(api_response.content))
                        })

    @app.get("/collections/{collection}/items")
    def get_collection_items(collection: str, bbox: str = '', limit=DEFAULT_LIMIT,
                             start_id: str = '', start: int = 0):
        api_response = server.handle_items_request(collection, start_id, start, bbox, limit)

        if api_response.http_response is not None:
            return Response(content=None, status_code=api_response.http_response.status_code)

        return Response(content=api_response.content,
                        headers={
                            "content-type": "application/geo+json",
                            "content-length": str(len(api_response.content))

                        })

    @app.get("/collections/{collection}/items/{feature_id}")
    def get_feature_info(collection: str, feature_id: str):
        api_response = server.handle_item_request(collection, feature_id)

        if api_response.http_response is not None:
            return Response(content=None, status_code=api_response.http_response.status_code)

        return Response(content=api_response.content,
                        headers={
                            "content-type": "application/geo+json",
                            "content-length": str(len(api_response.content))
                        })

    # endregion


    @app.get("/api")
    def api_definition():
        spec = get_custom_api()
        response = json_dumps_for_response(spec)

        return Response(content=response,
                        headers={
                            "content-type": "application/openapi+json;version=3.0",
                            "content-length": str(len(response))
                        })

    def get_custom_api():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="OGC API - Features server",
            description="Web API that conforms to the OGC API Features specification.",
            version="1.0",
            routes=app.routes,
        )

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    # endregion

    @app.get('/{path:path}', include_in_schema=False)
    def raise_404():
        return Response(content=None, status_code=404)


if __name__ == 'ogc_api.main':
    main()
