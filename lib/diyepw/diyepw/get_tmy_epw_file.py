import tempfile
import urllib.request as request
import re
import os
import shutil
from zipfile import ZipFile
from urllib.error import URLError

# Buffer for the EPW catalog, which is a large HTML file that we don't want to have to download anew every time
# a new EPW file is requested
_catalog_html = None

def get_tmy_epw_file(wmo_index:int, output_dir:str = None):
    """
    Given a WMO index, retrieve a TMY (typical meteorological year) EPW file for that location
    :param wmo_index:
    :param output_dir: Optional output directory - if not specified, the file will be saved to a temporary directory.
        If the directory already contains a TMY EWP file matching the requested WMO Index, then a new
        file will not be downloaded, we will just return that file's path
    :return: The path to the AMY EPW file
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp()

    # The sources we know of for TMY EPW files are http://climate.onebuilding.org and https://energyplus.net/weather;
    # we use the climate.onebuilding.org source here because it has all of the EPW files linked
    # from a single page, making it relatively easy and quick to find the right file.
    catalog_url = "http://climate.onebuilding.org/WMO_Region_4_North_and_Central_America/" \
                  "USA_United_States_of_America/"

    # If the HTML of the catalog page hasn't been downloaded yet, download it. The catalog page has links to
    # a set of TMY files for every WMO in the United States
    global _catalog_html
    if _catalog_html is None:
        # Retrieve the TMY EPW catalog for the requested year.
        try:
            with request.urlopen(catalog_url) as response:
                _catalog_html = response.read().decode('utf-8')
        except URLError:
            raise Exception(f"Failed to connect to {catalog_url} - are you connected to the internet?")

    # Find the filename in the catalog that matches the requested WMO index
    match = re.search(f'href="([^"]*\.{wmo_index}_TMY3\.zip)"', _catalog_html)
    if match is None:
        raise Exception(f"No file for WMO index {wmo_index} could be found at {catalog_url}")
    file_url = catalog_url + match.groups()[0]

    # Download the ZIP file and decompress it. It contains a number of files including the EPW that we are looking for.
    tmp_file_handle, tmp_file_path = tempfile.mkstemp()
    tmp_dir = tempfile.mkdtemp()
    with request.urlopen(file_url) as response:
        with open(tmp_file_handle, 'wb') as downloaded_file:
            downloaded_file.write(response.read())
    with ZipFile(tmp_file_path, 'r') as zip_file:
        zip_file.extractall(tmp_dir)

    # Move the EPW file from the temporary directory into which we extracted the ZIP file into the directory storing
    # our EPWs
    epw_file_name = file_url.split("/")[-1].replace(".zip", ".epw")
    epw_file_path = os.path.join(output_dir, epw_file_name)
    os.rename(os.path.join(tmp_dir, epw_file_name), epw_file_path)

    # Delete the temporary files created in this call
    os.unlink(tmp_file_path)
    shutil.rmtree(tmp_dir)

    return epw_file_path