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

meta_header = """\
<?xml version="1.0" encoding="UTF-8"?>
<ContentDBInstall VERSION="1.0">
 <Products>
  <Product VALUE="{pname}">
   <StoreID VALUE="{vendor}"/>
   <GlobalID VALUE="{guid}"/>
   <ProductToken VALUE="{pidx}"/>
   <Assets>"""
meta_asset = """\
    <Asset VALUE="{}"/>"""
meta_center = """\
   </Assets>
   <SupportAssets VALUE="/Runtime/Support/{vendor}_{pidx}_{metaname}.dsx">"""
meta_support = """\
    <SupportAsset VALUE="/{}"/>"""
meta_footer = """\
   </SupportAssets>
  </Product>
 </Products>
</ContentDBInstall>
"""
meta_file = "Content/Runtime/Support/{vendor}_{pidx}_{metaname}.dsx"
meta_script = "Content/Runtime/Support/{vendor}_{pidx}_{metaname}.dsa"
meta_image = "Content/Runtime/Support/{vendor}_{pidx}_{metaname}.jpg"
support_meta_file = "Runtime/Support/{vendor}_{pidx}_{metaname}.dsx"
support_meta_script = "Runtime/Support/{vendor}_{pidx}_{metaname}.dsa"
support_meta_image = "Runtime/Support/{vendor}_{pidx}_{metaname}.jpg"
scriptbytes ="""\
// DAZ Studio version 4.9.1.30 filetype DAZ Script

if( App.version >= 67109158 ) //4.0.0.294
{
        var oFile = new DzFile( getScriptFileName() );
        var oAssetMgr = App.getAssetMgr();
        if( oAssetMgr )
        {
                oAssetMgr.queueDBMetaFile( oFile.baseName() );
        }
}
"""
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
vendormap = {
    'DAZ'  : 'DAZ_3D',
    'WDC'  : 'Wilmap',
    'HW'   : 'Hivewire3D',
    'RDNA' : 'RuntimeDNA',
    'MDC'  : 'Most-Digital',
    'SCG'  : 'ShareCG',
    'RO'   : 'Renderosity',
    'RE'   : 'Renderotica',
    'ME'   : 'Esemwy',
}

manifest_header = """\
<DAZInstallManifest VERSION="0.1">
 <GlobalID VALUE="{guid}"/>"""
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
asset_types = [
 '.hd2', '.pp2', '.pz3', '.mc6', '.cm2',
 '.dsb', '.dsf', '.ds',  '.daz', '.lt2',
 '.duf', '.dse', '.pz2', '.cr2', '.dsa',
 '.hr2']
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

def addDirContent(zip, thePath, info):
    prefix = os.path.dirname(thePath)

    manifest = [manifest_header.format(**info)]
    metadata = [meta_header.format(**info)]
    asset = []
    support = []

    for dirpath, dirnames, filenames in os.walk(thePath):
        for name in filenames:
            if badFile(name):
                continue
            fullPath = os.path.join(dirpath, name)
            filePath = makeOutputPath(fullPath[len(prefix)+1:], info['pname'])
            ext = os.path.splitext(fullPath)[1]
            if ext in asset_types:
                asset.append(meta_asset.format(fullPath))
            else:
                support.append(meta_support.format(fullPath))
            zip.writestr(filePath, open(fullPath,'r').read())
            filePath = filePath.replace('&', '&amp;')
            manifest.append(manifest_line.format(filePath))
    support.append(meta_support.format(support_meta_file.format(**info)))
    support.append(meta_support.format(support_meta_script.format(**info)))
    support.append(meta_support.format(support_meta_image.format(**info)))
    manifest.append(manifest_line.format(meta_script.format(**info)))
    if os.path.exists(info['thumb']):
        manifest.append(manifest_line.format(meta_image.format(**info)))
    manifest.append(manifest_line.format(meta_file.format(**info)))

    metadata.append('\n'.join(asset))
    metadata.append(meta_center.format(**info))
    metadata.append('\n'.join(support))
    metadata.append(meta_footer)

    manifest.append(manifest_footer)
    return manifest, metadata

def addZipContent(zip, thePath, info):
    manifest = [manifest_header.format(**info)]
    metadata = [meta_header.format(**info)]
    asset = []
    support = []

    with ZipFile(thePath, 'r') as infile:
        for fullPath in infile.namelist():
            if badFile(fullPath):
                continue
            finfo = infile.getinfo(fullPath)
            if finfo.external_attr & 16:
                continue
            filePath = makeOutputPath(fullPath, info['pname'])
            ext = os.path.splitext(fullPath)[1]
            if ext in asset_types:
                asset.append(meta_asset.format(fullPath))
            else:
                support.append(meta_support.format(fullPath))
            zip.writestr(filePath, infile.read(fullPath))
            filePath = filePath.replace('&', '&amp;')
            manifest.append(manifest_line.format(filePath))
    support.append(meta_support.format(support_meta_file.format(**info)))
    support.append(meta_support.format(support_meta_script.format(**info)))
    support.append(meta_support.format(support_meta_image.format(**info)))
    manifest.append(manifest_line.format(meta_script.format(**info)))
    if os.path.exists(info['thumb']):
        manifest.append(manifest_line.format(meta_image.format(**info)))
    manifest.append(manifest_line.format(meta_file.format(**info)))

    metadata.append('\n'.join(asset))
    metadata.append(meta_center.format(**info))
    metadata.append('\n'.join(support))
    metadata.append(meta_footer)

    manifest.append(manifest_footer)
    return manifest, metadata

def makeInfo(productid, productpart, productname, vendor):
    info = {
        'orderdate'     : time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'installerdate' : time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'pidx'          : productid,
        'psubidx'       : productpart,
        'pname'         : productname,
        'orderid'       : randint(1000000,9999999),
        'guid'          : str(uuid.uuid4()),
        'vendor'        : vendor,
        'metaname'      : productname.replace('/','_').replace('\\\\','_').replace(' ','_'),
        'thumb'         : 'thumbs/{}.jpg'.format(int(str(productid)[1:]))
    }
    return info

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
    vendor = ""
    if args.source is not None:
        vendor = vendormap[args.source.upper()]
    else:
        key, = [k for k, v in a.items() if v == args.prefix]
        vendor = vendormap[key]

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

    info = makeInfo(productid, args.productpart, args.productname, vendor)
    print 'Creating {} from {}'.format(zipname, args.contents)
    # sys.exit(1)
    with ZipFile(os.path.join(os.getcwd(), zipname), 'w') as zip:
        if is_zipfile(args.contents):
            manifest, metadata = addZipContent(zip, args.contents, info)
        else:
            manifest, metadata = addDirContent(zip, args.contents, info)
        manifestbytes = "\n".join(manifest)
        metadatabytes = "\n".join(metadata)
        supplementbytes = supplement.format(args.productname)
        meta_script_name = meta_script.format(**info)
        meta_file_name = meta_file.format(**info)
        meta_image_name = meta_image.format(**info)
        zip.writestr(meta_script_name, scriptbytes)
        zip.writestr(meta_file_name, metadatabytes)
        try:
            metaimagebytes = open(info['thumb'],'rb').read()
            zip.writestr(meta_image_name, metaimagebytes)
        except:
            pass
        zip.writestr('Supplement.dsx', supplementbytes);
        zip.writestr('Manifest.dsx', manifestbytes)


if __name__ == "__main__":
    main()
