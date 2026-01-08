# ERDDAP2WFS

**ERDDAP2WFS** is a project allowing ERDDAP datasets to be translated and exported as WFS OGC API server that is mimially compliant with the [OGC API - Features (OAPIF)](https://docs.opengeospatial.org/is/17-069r3/17-069r3.html) standard.

**ERDDAP Dataset Compatibility:**

Designed to work with OTN Slocum Glider datasets, but should work with any dataset that has time/lat/lon

Most to least compatible:

1. Works best with variables `m_gps_lat/m_gps_lon` to find surfacings
2. If those variables aren't in the ERDDAP dataset, it uses `profile_id` and `depth` to try and find likely surfacings
3. If all else fails it will just use `time/lat/lon`

## Usage

### Runing

* Configure the `ERDDAP` environment variable in the [docker-compose.yml](./docker-compose.yml)
* Run with: `docker compose up`

### QGIS

* In the top menubar navigate to `Layer > Data Source Manager`
* In the dialog box's side menu go to `WFS / OGC API - Features`
* Click `New` and enter the address of the computer running the server under `URL`, eg: `http://localhost:8000/`
* To verify it's working, click `Detect` button next to the `Version` box, it should auto detect the version, if not check to make sure the IP is correct and there are no errors coming from the server.
* Now when you click the `Connect` button you should see all the ERDDAP layers from the configured ERDDAP.

**Available API endpoints:**

* */docs*
* */collections*
* */collections/{collection}*
* */collections/{collection}/items*
* */collections{collection}/items/{feature_id}*

## Acknowledgements

Forked from: [python-wfs-server](https://gitlab.com/labiang/python-wfs-server)

## Development Plan

This is a WIP project. However, the main branch is, and should continue be functional.

* [X] python-wfs-modification
  * Modified codebase to work with custom ERDDAP proxy code instead of geojson files
  * Removed unused code (mostly related to tiles)
  * Fixed some data structure bugs
  * Updated docker files
* [X] ERDDAP Datasets as collections
  * Translate ERDDAP dataset to OGC API (collection)
  * Convert dataset only when requests, caches the dataset for future use, since ERDDAP is slow
* [ ] Refactor server code (was originally made just as a proof of concept)
* [ ] Translate ERDDAP dataset to be path or points (currently just points)
* [ ] Stream data to eliminate request freezing for long periods of time (again, since ERDDAP is slow)
  * I think this can only be done with points
* [ ] Fix tests, I guess
