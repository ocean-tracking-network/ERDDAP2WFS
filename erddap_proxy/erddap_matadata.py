from ogc_api.data_structures import Collection, CollectionMetadata
from ceotr_erddap_proxy.erddapy_proxy import CeotrErddapProxy
import geojson
import json
from datetime import datetime
import requests
from ogc_api import geometry
import pandas as pd

class ERDDAPCollections():
    def __init__(self, erddap_server):
        self.erddap_server = erddap_server
        self.e = CeotrErddapProxy(erddap_server)
        
        self.erddap_server = erddap_server
        self.meta = ERDDAPMetadata(erddap_server, self.e)
        self.data = ERDDAPData(erddap_server, self.e)
        self.cache = {}

    def get_collections(self):
        # for dataset_id in self.meta.get_erddap_datasets():
        #     self.get_collection_as_data(dataset_id)
        return self.meta.get_erddap_as_collections()
    
    def get_collection_as_meta(self, dataset_id):
       if dataset_id in self.meta.get_erddap_datasets():
           return self.meta.create_erddap_collection(dataset_id)

    def get_collection_as_data(self, dataset_id):
        collection = self.get_collection_as_meta(dataset_id)
        if dataset_id not in self.cache:
            self.cache[dataset_id] = self.data.get_erddap_as_collection(dataset_id, collection)
        return self.cache[dataset_id]

class ERDDAPMetadata():
    def __init__(self, erddap_server: str, erddap_proxy: CeotrErddapProxy):
        self.erddap_server = erddap_server
        self.e = erddap_proxy
        
    def get_erddap_datasets(self) -> list[str]:
        self.e.constraints = {}
        dataset_ids = self.e.get_dataset_ids()
        dataset_ids.remove("allDatasets")
        return dataset_ids
    
    def create_erddap_collection(self, dataset_id) -> Collection:
        collection = Collection()
        c_meta = CollectionMetadata(dataset_id, 
                                    dataset_id,
                                    None)
        collection.metadata = c_meta
        return collection
        
        
    def get_erddap_as_collections(self):
        collections = []
        dataset_ids = self.get_erddap_datasets()
        # dataset_ids = [dataset_ids[50]]
        for dataset_id in dataset_ids:
            collection = self.create_erddap_collection(dataset_id)
            collections.append(collection)
        return collections

    
class ERDDAPData():
    def __init__(self, erddap_server, erddap_proxy: CeotrErddapProxy):
        self.e = erddap_proxy
        self.erddap_server = erddap_server

    def detect_dataset_type(self, dataset_id):
        metadata_url = self.e.get_info_url(dataset_id, response="csv")
        df = pd.read_csv(metadata_url)
        variable_values = df["Variable Name"].values
        if "m_gps_lat" in variable_values:
            return "m_gps"
        elif "profile_id" in variable_values:
            return "profile_id"
        else:
            return "latlon"

    def _get_erddap_geojson(self, dataset_id) -> geojson:
        self.e.dataset_id = dataset_id

        dataset_type = self.detect_dataset_type(dataset_id)
        download_url = ""
        self.e.constraints = {}
        self.e.response = "geoJson"
        if dataset_type == "m_gps":
            self.e.variables = ["time", "latitude", "longitude", "profile_id"]
            self.e.constraints = {
                "m_gps_lat!=": float('NaN')
            }
            download_url = self.e.get_download_url()
            download_url = download_url.replace("!=nan", "!=NaN")
        elif dataset_type == "profile_id":
            self.e.variables = ["time", "latitude", "longitude", "profile_id"]
            self.e.constraints = {
                "depth<": 10 
            }
            download_url = self.e.get_download_url()
        elif dataset_type == "latlon":
            self.e.variables = ["time", "latitude", "longitude"]
            download_url = self.e.get_download_url()
            
        print(download_url)

        res = requests.get(download_url)
        return geojson.loads(json.dumps(res.json()))

    def convert_to_collection(self, erddap_geojson: geojson, collection: Collection) -> Collection:
        # last_profile_id = 0
        # index_offset = 0
        # latlons = []
        # for index, feature in enumerate(erddap_geojson.features):
        #     if "profile_id" in feature.properties:
        #         profile_id = feature.properties["profile_id"]
        #         if profile_id == last_profile_id:
        #             index_offset += 1
        #             continue
        #         else:
        #             last_profile_id = profile_id
        #     latlons.append(feature["geometry"]["coordinates"])
        #     # id_int = int(datetime.fromisoformat(feature.properties["time"].removesuffix("Z")).timestamp())
        #     # id_str = str(id_int)
        #     # collection.id.append(id_str)
        #     # collection.by_id[id_str] = index - index_offset
        #     # feature["id"] = id_str
        #     # collection.feature.append(geojson.dumps(feature, ensure_ascii=False, separators=(',', ':')))
        #     collection.bbox = []
        #     collection.bbox.append(geometry.compute_bounds(feature.geometry))
        #     # 
        #     center = collection.bbox[0].get_center()
        #     collection.web_mercator = []
        #     collection.web_mercator.append(geometry.project_web_mercator(center))
        # collection.feature.append(json.dumps({
        #     "id": "1",
        #     "type": "Feature",
        #     "geometry": {
        #         "type": "LineString",
        #         "coordinates": latlons
        #     }
        # }))
        # return collection

        last_profile_id = 0
        index_offset = 0
        for index, feature in enumerate(erddap_geojson.features):
            # if "profile_id" in feature.properties:
            #     profile_id = feature.properties["profile_id"]
            #     if profile_id == last_profile_id:
            #         index_offset += 1
            #         continue
            #     else:
            #         last_profile_id = profile_id
            id_int = int(datetime.fromisoformat(feature.properties["time"].removesuffix("Z")).timestamp())
            id_str = str(id_int)
            collection.id.append(id_str)
            collection.by_id[id_str] = index - index_offset
            feature["id"] = id_str
            collection.feature.append(geojson.dumps(feature, ensure_ascii=False, separators=(',', ':')))
            collection.bbox.append(geometry.compute_bounds(feature.geometry))
            # 
            center = collection.bbox[index-index_offset].get_center()
            collection.web_mercator.append(geometry.project_web_mercator(center))
        return collection
# 


    def get_erddap_as_collection(self, dataset_id, collection):
        erddap_geojson = self._get_erddap_geojson(dataset_id)
        if erddap_geojson:
            collection = self.convert_to_collection(erddap_geojson, collection)
            return collection
        else:
            return Collection()
            

    

        
if __name__ == '__main__':
    e = ERDDAPMetadata("http://129.173.20.186:8080/erddap/")
    e.get_erddap_as_collections()