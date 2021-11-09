import os.path
from os import listdir

import zlib, zipfile
import hashlib
import json
from json import JSONEncoder

FILE_LIST_FILENAME = "bundle_files.txt"
INCLUDE_SIGNATURE_FILE = True

MIRGOR_SIGNATURE_FILENAME = "mirgsign.txt"
OUTPUT_MANIFEST_FILENAME = "manifest.json"
OUTPUT_BUNDLE_FILENAME = "updatebundle_autocreated.zip"

class ManifestDescriptor():
  def __init__(self):
    self.applications = []

class ApplicationDescriptor():
  def __init__(self):
    self.path = None
    self.dest = None
    self.compressed = None
    self.size = None
    self.hash = None

class CustomEncoder(JSONEncoder):
  def default(self, o):
    return o.__dict__

def create_manifest(filename):
  manifest = ManifestDescriptor()
  with open(filename) as file_list:
    line = file_list.readline()
    line_number = 0

    while line:
      app = ApplicationDescriptor()
      split_line = line.split()

      if len(split_line) != 2:
        raise RuntimeError(f"Bundle file list format error at line {line_number}. Need file and path")
      
      bundle_file = split_line[0]
      bundle_path = split_line[1]

      app.dest = bundle_path

      if not os.path.isfile(bundle_file):
        if os.path.isdir(bundle_file):
          dir_files = listdir(bundle_file)
          zf = zipfile.ZipFile(bundle_file + ".zip", mode = "w")

          try:
            for file_name in dir_files:
              zf.write(bundle_file + "/" + file_name, file_name, compress_type=zipfile.ZIP_STORED)
          except FileNotFoundError as err:
            zf.close()
            raise err
          finally:
            zf.close()

          bundle_file += ".zip"
          app.compressed = True
        else:
          raise RuntimeError(f"Bundle file '{bundle_file}' does not exist!")
      else:
        app.compressed = False
      
      app.path = bundle_file
      app.size = os.path.getsize(bundle_file)

      sha256_hash = hashlib.sha256()

      print(f"Calculating hash of file {bundle_file}...")

      with open(bundle_file, "rb") as f:
        for byte_block in iter(lambda: f.read(4096),b""):
          sha256_hash.update(byte_block)

      app.hash =  sha256_hash.hexdigest()

      manifest.applications.append(app)

      line_number += 1
      line = file_list.readline()
  
  return manifest

if __name__ == "__main__":
  try:
    manifest = create_manifest(FILE_LIST_FILENAME)

    print("Manifest file created:")

    manifest_json = json.dumps(manifest, cls=CustomEncoder)
    print(manifest_json)

    with open(OUTPUT_MANIFEST_FILENAME, "w") as text_file:
      text_file.write(manifest_json)
    
    # TODO: Create update bundle
    zf = zipfile.ZipFile(OUTPUT_BUNDLE_FILENAME, mode = "w")

    try:
      bundle_files = [OUTPUT_MANIFEST_FILENAME]

      if INCLUDE_SIGNATURE_FILE == True:
        bundle_files.append(MIRGOR_SIGNATURE_FILENAME)

      bundle_files.extend([a.path for a in manifest.applications])

      print("Bundle files:")
      print(bundle_files)

      for file_name in bundle_files:
        zf.write(file_name, file_name, compress_type=zipfile.ZIP_STORED)
    except FileNotFoundError as err:
      zf.close()
      raise err
    finally:
      zf.close()
  except Exception as e:
    print(e)