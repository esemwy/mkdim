#!/usr/bin/python
import uuid
import os
from zipfile import ZipFile, is_zipfile
import sys
import time
from random import randint
import argparse
import re
import hashlib
from math import log10

# To avoid confusing with DAZ3D product codes, some special ranges need to be used, so the following ranges has been reserved:
#
# - 2xxxxxxx    for Wilmap's Digital Creations products, where xxxxxxx is SKU number.
# - 3xxxxxxx    for Hivewire3D                         , where xxxxxxx is the product number without the prefix letter.
# - 4xxxxxxx    for RuntimeDNA                         , where xxxxxxx is the product number without the prefix letter.
# - 5xxxxxxx    for Most Digital Creations products    , where xxxxxxx is the product number without the prefix letter.
# - 6xxxxxxx    for Sharecg products                   , where xxxxxxx is the reference number.
# - 7xxxxxxx    for Renderosity products               , where xxxxxxx is RO number.
# - 8xxxxxxx    for Renderotica products               , where xxxxxxx is SKU number.
# - 9xxxxxxx    is reserved for your own products      , and can be numbered as your convenience.
#
# ie: the SKU 41367 (Renderotica SFD pubic hair for V5) will be converted in an zip archive named IM80041367-00_SFDPubicHairForV5.zip
#
# Another tips is to add the "CVN" letters at the end of the productname, so that it can be easily identified as "converted".

idmap = {
    'DAZ'  : 0,
    'WDC'  : 2,
    'HW'   : 3,
    'RDNA' : 4,
    'MDC'  : 5,
    'SCG'  : 6,
    'RO'   : 7,
    'RE'   : 8,
    'ME'   : 9,
}

dsx = """\
<?xml version="1.0" encoding="UTF-8"?>
<ProductSupplement VERSION="0.1">
 <ProductName VALUE="{pname}"/>
 <ProductStoreIDX VALUE="{pidx}-{psubidx}"/>
 <UserOrderId VALUE="{orderid}"/>
 <UserOrderDate VALUE="{orderdate}"/>
 <InstallerDate VALUE="{installerdate}"/>
 <ProductFileGuid VALUE="{guid}"/>
 <InstallTypes VALUE="Content"/>
 <ProductTags VALUE="DAZStudio4_5"/>
</ProductSupplement>
"""
manifest_header = """\
<DAZInstallManifest VERSION="0.1">
 <GlobalID VALUE="{}"/>"""
manifest_line = """ <File TARGET="Content" ACTION="Install" VALUE="{}"/>"""
manifest_footer = """</DAZInstallManifest>
"""

supplement = """\
<ProductSupplement VERSION="0.1">
 <ProductName VALUE="{}"/>
 <InstallTypes VALUE="Content"/>
 <ProductTags VALUE="DAZStudio4_5"/>
</ProductSupplement>
"""
def zipVerified(thePath):
    rootdirs = set(['data', 'Runtime', 'People', 'Scripts', 'Shaders', 'Presets', 'Shader Presets', 'Materials'])
    with ZipFile(thePath,'r') as zip:
        names = zip.namelist()
        dirs = set([ i[:i.index('/')] for i in names if i.count('/')])

    if not rootdirs.intersection(dirs):
        return False
    return True

def badFile(name):
    if (  (name.lower().find('@eadir') != -1)
        or name.lower().endswith('.ds_store')
        or name.lower().endswith('thumbs.db')):
        return True
    return False

def makeOutputPath(name, product):
    if (   ('/' not in name)
        or (name.lower().startswith('readme'))
        or (name.lower().startswith('documentation'))):
        return os.path.join('Content', 'Documentation', product, os.path.basename(name))
    else:
        return os.path.join('Content',name)

def addDirContent(zip, thePath, product):
    prefix = os.path.dirname(thePath)
    manifest = [manifest_header.format(str(uuid.uuid4()))]

    for dirpath, dirnames, filenames in os.walk(thePath):
        for name in filenames:
            if badFile(name):
                continue
            fullPath = os.path.join(dirpath, name)
            filePath = makeOutputPath(fullPath[len(prefix)+1:], product)

            zip.writestr(filePath, open(fullPath,'r').read())
            filePath = filePath.replace('&', '&amp;')
            manifest.append(manifest_line.format(filePath))

    manifest.append(manifest_footer)
    return manifest

def addZipContent(zip, thePath, product):
    manifest = [manifest_header.format(str(uuid.uuid4()))]

    with ZipFile(thePath, 'r') as infile:
        for name in infile.namelist():
            if badFile(name):
                continue
            info = infile.getinfo(name)
            if info.external_attr & 16:
                continue
            filePath = makeOutputPath(name, product)

            zip.writestr(filePath, infile.read(name))
            filePath = filePath.replace('&', '&amp;')
            manifest.append(manifest_line.format(filePath))

    manifest.append(manifest_footer)
    return manifest

def makeDSX(dsxname, productid, productpart, productname):
    dsxinfo = {
        'orderdate'     : time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'installerdate' : time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'guid'          : str(uuid.uuid4()),
        'pidx'          : productid,
        'psubidx'       : productpart,
        'pname'         : productname,
        'orderid'       : randint(1000000,9999999),
    }
    dsxbytes = dsx.format(**dsxinfo)

    with open(os.path.join(os.getcwd(), dsxname),'w') as dsxfile:
        dsxfile.write(dsxbytes)

def main():
    parser = argparse.ArgumentParser(description='Make DAZ Install manager ZIP and metadata.')
    parser.add_argument('contents', metavar='directory or zip', type=str, help='Product input source (directory or zip file)')
    parser.add_argument('--prefix', dest='prefix', type=int, help='Manufacturer prefix')
    parser.add_argument('--source', dest='source', type=str, default='me', choices=(idmap.keys() + map(str.lower, idmap.keys())), help='Manufacturers Product ID')
    parser.add_argument('--id', dest='productid', required=True, type=str, help='Manufacturers Product ID')
    parser.add_argument('--part', dest='productpart', default=1, type=int, help='Part of product')
    parser.add_argument('--name', dest='productname', required=True, type=str, help='Name of product')

    args = parser.parse_args()

    prefix = args.prefix if args.prefix is not None else idmap[args.source.upper()]

    if is_zipfile(args.contents):
        if zipVerified(args.contents):
            pass
        else:
            print "Input ZIP", args.contents, "is not organized correctly. Extract and retry with directory."
            return
    elif os.path.isdir(args.contents):
        pass
    else:
        print "Input must be either a directory or zipfile"
        return

    try:
        val = int(args.productid.encode('utf-8'))
    except ValueError:
        md = hashlib.sha224()
        md.update(args.productid.encode('utf-8').upper())
        val = int(md.hexdigest(),16)%1000000

    n = int(log10(prefix))
    if n not in (0,1):
        print "Illegal prefix, maximum of two digits"
        return
    k = int(10000000/10**n)
    productid = k*prefix + val
    productname = re.sub('[^A-Za-z0-9]', '', args.productname)
    zipname = "IM{:08d}-{:02d}_{}.zip".format(productid, args.productpart, productname)
    dsxname = "IM{:08d}-{:02d}_{}.dsx".format(productid, args.productpart, productname)
    print 'Creating {} from {}'.format(zipname, args.contents)
    # sys.exit(1)
    with ZipFile(os.path.join(os.getcwd(), zipname), 'w') as zip:
        if is_zipfile(args.contents):
            manifest = addZipContent(zip, args.contents, productname)
        else:
            manifest = addDirContent(zip, args.contents, productname)
        manifestbytes = "\n".join(manifest)
        supplementbytes = supplement.format(args.productname)
        zip.writestr('Supplement.dsx', supplementbytes);
        zip.writestr('Manifest.dsx', manifestbytes)

    # makeDSX(dsxname, productid, args.productpart, args.productname)

if __name__ == "__main__":
    main()
