"""
VicExtract.py will pull COLOR, YEAR, MAKE, MODEL, BODY, LICENSE STATE,LICENSE NUMBER,LICENSE EXPIRATION, VIN, and REGISTERED OWNER from PDF's

Loops through all PDFs in a folder and creates a CSV with the same name. Ex: info.pdf becomes info.pdf.csv

It organizes the CSV with column headings for color, year, make, model, body, license state, lincense number, license expiration, VIN, and Registered Owner

License: GPL 3.0
Date: 2/10/2026
Version: 1.0
Author: Alan Mullin

Known issues:
- sometimes has issues with the last vehicle record in a file

"""
from pypdf import PdfReader
import os, argparse, sys, json,csv

bVerbose = False

'''
getColor() finds color info in a list. Returns "COLOR_UNK" if none found.
'''
def getColor(line_list=None):
    if line_list is None or line_list == []:
        print(f"getColor(): empty list...")
        return "COLOR_NOLISTPASSED"
        
    for line in line_list:
        if 'Color:' in line:
            color = line
            color = color.replace('Primary Color: ','') # Liferaft
            color = color.replace('Color: ', '') # TLOxp
            if bVerbose:
                print(f"getColor(): Found {color}.")
            return color
        else:
            continue
    return "COLOR_UNK" # No Color found.    

'''
getRO() looks for Registered Owner info in a group of strings. It also has a flag for Liferaft or TLOxp Returns "RO_UNKNOWN" if none found.
'''
def getRO(line_list=None,TLOflag=True):
    if line_list is None or line_list == []:
        print(f"getRO(): empty list...")
        return "RO_NOLISTPASSED"
    
    if bVerbose:
        print(f"getRO(): Looking in {line_list}")    
    reg_info = ''
    address = ''
    # Are we looking at Liferaft or TLOxp?
    if not TLOflag: # Liferaft
        for line in line_list:
            if "Regsitrant:" in line or "Owner:" in line:
                reg_info = line
                reg_info = reg_info.replace("Registrant: ", "")
                reg_info = reg_info.replace("Owner: ","")
                continue
            if "Address:" in line:
                address = line
                address = address.replace("Mailing Address: ", "")
                continue
    else:
        for ind, line in enumerate(line_list):
            if 'tle Hol' in line:
                # we need the next two lines
                reg_info = line_list[ind+1]
                try:
                    address = line_list[ind+2]
                except IndexError:
                    address = "ADDRESS_UNK"
                reg_info = reg_info.replace('[ View Person Record ]','')
                break
                
    if reg_info and address:
        reg_info += ' ' + address
        if bVerbose:
            print(f"getRO(): Found {reg_info}")
        return reg_info            
                
    return "RO_UNKNOWN"
                

'''
 getVIN() pulls the VIN from a group of lines, if possible. It takes a list of strings as a parameter
'''
def getVIN(line_list=None):
    if line_list is None or line_list == []:
        print(f"getVIN(): empty list...")
        return "VIN_NOLISTPASSED"
        
    for line in line_list:
        if 'VIN:' in line:
            vin = line
            vin = vin.replace('VIN: ', '')
            if bVerbose:
                print(f"getVIN(): Found {vin}.")
            return vin
        else:
            continue
    return "VIN_UNK" # No VIN found.

'''
getBody() pulls body style info from a list of strings. Returns "BODY_UNK" if nothing found.
'''
def getBody(line_list=None):
    if line_list is None or line_list == []:
        print(f"getBody(): empty list...")
        return "BODY_NOLISTPASSED"
        
    for line in line_list:
        if 'Body Style:' in line:
            body = line
            body = body.replace('Body Style: ', '')
            if bVerbose:
                print(f"getBody(): Found {body}.")
            return body
        else:
            continue
    return "BODY_UNK" # No Body info found.    

'''
getState() finds the state info in a list of strings. It returns "STATE_UNK" if none found.
'''
def getState(line_list=None,TLOflag=True):
    if line_list is None or line_list == []:
        print(f"getState(): empty list...")
        return "STATE_NOLISTPASSED"
        
    if not TLOflag:    
        for line in line_list:
            if 'State:' in line:
                lic_state = line
                lic_state = lic_state.split()
                lic_state = lic_state[-1]
                if bVerbose:
                    print(f"getState(): Found {lic_state}.")
                return lic_state
            else:
                continue
    else:
        return # porcess_TLO() handles this
    return "STATE_UNKNOWN"

'''
getPlate() finds license plate info in a list for strings. It returns "PLATE_UNK" if none found.
'''
def getPlate(line_list=None,TLOflag=True):
    if line_list is None or line_list == []:
        print(f"getPlate(): empty list...")
        return "PLATE_NOLISTPASSED"
        
    if not TLOflag:    
        for line in line_list:
            if 'Plate:' in line:
                lic_info = line
                if bVerbose:
                    print(f"getPlate(): Found {lic_info}.")
                return lic_info
            else:
                continue
    else:
        #TLOxp file
        for line in line_list:
            if 'Current Tag' in line:
                lic_info = line
                lic_info = lic_info.replace('Most Current Tag #: ','')
                lic_info = lic_info.split()
                return_val = lic_info[0] + ' ' + lic_info[1]
                return return_val
    return "PLATE_UNK"

'''
getTLOExp() pulls the expiration from a list of strings. Only called by process_TLO(). Returns EXP_UNK if none found.
'''
def getTLOExp(line_list=None):
    if line_list is None or line_list == []:
        print(f"getTLOExp(): empty list...")
        return "EXP_NOLISTPASSED"
        
    for line in line_list:
        if 'CurrentOwner' in line:
            lic_exp = line
            lic_exp = lic_exp.split()
            return lic_exp[-1]
    return "EXP_UNK"

'''
 build_entry_str() takes all of the values we want to save and puts them in a string to add to the list of vehicles
'''
def build_entry_str(color="",year="",make="",model="",body="",lic_state="",lic_num="",lic_exp="1/1/1800",vin="AAA12345678912345",ro_info=""):
    if lic_exp == 'Information':
        lic_exp = '1/1/1800'
    
    # we have a complete entry
    json_string = '{ \"color\": \"' + color + '\"'
    json_string += ', \"year" : \"' + year + '\"'
    json_string += ', \"make\" : \"' + make + '\"'
    json_string += ', \"model\" : \"' + model + '\"'
    json_string += ', \"body\" : \"' + body + '\"'
    json_string += ', \"lic_state\" : \"' + lic_state + '\"'
    json_string += ', \"lic_num\" : \"' + lic_num + '\"'
    json_string += ', \"lic_exp\" : \"' + lic_exp + '\"'
    json_string += ', \"vin\" : \"' + vin + '\"'
    json_string += ', \"registered_owner\" : \"' + ro_info + '\"'
    json_string += '}'
    if bVerbose:
        print(f"build_entry_str(): {json_string}")
    return json_string

'''
process_Life() reads a pDF file, links all the pages together, breaks them up by lines, and looks for vehicle information. It assumes that the PDF coming to it could contain vehicle information.
It applies some logic needed specifically by Liferaft formatted PDF files.
'''
def process_Life(fname=None):
    if fname is None:
        print(f"process_Life: file name must be specified.")
        exit(1)
    
    vehicle_list = []
    vehicle_json = []
    PDFText = "" # We load the PDF into a giant string
    
    # Process file
    vic_infile = 0
    print(f"Scraping {fname}...")
    reader = PdfReader(fname) # PDF File
        
    # Stich all the pages into a long string, and then make it a list of strings
    total_pages = len(reader.pages)
    for p,page in enumerate(reader.pages):
        page_text = page.extract_text()
        PDFText += page_text            
    pdf_lines = PDFText.splitlines()
    
    # remove extranesous line
    for line in pdf_lines:
        if 'LICENSED INVESTIGATOR' in line:
            pdf_lines.remove(line)
            continue
        if 'Page' in line:
            pdf_lines.remove(line)
            continue
        if 'Weight' in line:
            pdf_lines.remove(line)
            continue
        if 'MSRP' in line:
            pdf_lines.remove(line)
            continue
        if 'Height' in line:
            pdf_lines.remove(line)
            continue
        if 'Width' in line:
            pdf_lines.remove(line)
            continue
        if 'Wheel' in line:
            pdf_lines.remove(line)
            continue
        if 'Plant:' in line:
            pdf_lines.remove(line)
            continue
        if 'Fuel' in line:
            pdf_lines.remove(line)
            continue
        if 'Engine' in line:
            pdf_lines.remove(line)
            continue
        if 'Transmission' in line:
            pdf_lines.remove(line)
            continue
    
    color = year = make = model = body = lic_state = lic_num = lic_exp = vin = ro_info = "UNK"
    for l, line in enumerate(pdf_lines):
        vehicle_chunk = []
        
        if "VIN: " in line: # found a Motor Vehicles entry, grab 22 lines
            ind = 0
            while ind < 23:
                try:
                    vehicle_chunk.append(pdf_lines[l+ind])
                    if bVerbose:
                        print(f"Grabbing {pdf_lines[l+ind]}")
                    ind += 1
                except IndexError:
                    break
                    
            color = getColor(vehicle_chunk)
            year = "LR_YEARUNK" # Liferaft does not contain this info
            make = "LR_MAKEUNK"
            model = "LR_MODELUNK"
            vin = getVIN(vehicle_chunk)
            body = getBody(vehicle_chunk)
            lic_state = getState(vehicle_chunk,False)
            lic_info = getPlate(vehicle_chunk,False)
            if lic_info != "PLATE_UNK":
                lic_info = lic_info.split()
                lic_num = lic_info[1] # There are three elements
                lic_exp = lic_info[-1]
                lic_exp = lic_exp[1:]
                lic_exp = lic_exp[:-1]
            ro_info = getRO(vehicle_chunk, False)

            vic_infile += 1
            vic_str = build_entry_str(color,year,make,model,body,lic_state,lic_num,lic_exp,vin,ro_info)
            vehicle_list.append(vic_str)
            color = year = make = model = body = lic_state = lic_num = lic_exp = vin = ro_info = "UNK" 
    
    # convert the strings to JSON
    for vic in vehicle_list:
        if bVerbose:
            print(f"process_Life(): Adding {vic}...")
        res = json.loads(vic)
        vehicle_json.append(res)
        
    # save the vehicle list to a CSV file now
    try:
        keys = vehicle_json[0].keys()
    except IndexError:
        return # No vehicle entries
    fname = fname + ".csv"
    with open(fname, 'w', newline='') as csvout:
        dictwriter = csv.DictWriter(csvout, keys)
        dictwriter.writeheader()
        dictwriter.writerows(vehicle_json)        
'''
process_TLO() is just like process_Life() but has logic for the peculiarites of TLOxp formatted PDF files.
'''
def process_TLO(fname=None):
    if fname is None:
        print(f"process_TLO: file name must be specified.")
        exit(1)
    
    vehicle_list = []
    vehicle_json = []
    vic_total = 0
    PDFText = "" # We load the PDF into a giant string
    
    # Process file
    vic_infile = 0
    print(f"Scraping {fname}...")
    reader = PdfReader(fname) # PDF File
        
    # Stitch all the pages into a long string
    total_pages = len(reader.pages)
    for p,page in enumerate(reader.pages):
        page_text = page.extract_text()
        PDFText += page_text
            
    pdf_lines = PDFText.splitlines()    
    color = year = make = model = body = lic_state = lic_num = lic_exp = vin = ro_info = "UNK"
    for l, line in enumerate(pdf_lines):
        vehicle_chunk = []
            
        # Look for what we want
        if "Subject" in line or "Result Found" in line: #we have hit a new vehicle record
            print(f"New vehicle entry...")
            ind = 1
            try:
                while ind < 32:
                    vehicle_chunk.append(pdf_lines[l+ind])
                    if bVerbose:
                        print(f"Grabbing {pdf_lines[l+ind]}")
                    ind += 1
            except IndexErrror:
                break
            
            color = getColor(vehicle_chunk)
            # get year, make, model
            string = vehicle_chunk[0] # e.g. 2014 CHEVROLET MALIBU (Michigan, Ohio)
            if 'Page' in string:
                string = vehicle_chunk[1] # had a page break right before the vehicle info            
            string = string.split()
            year = string[0] # 2014
            make = string[1] # CHEVROLET
            model = string[2] # MALIBU
            body = getBody(vehicle_chunk)
            lic_info = getPlate(vehicle_chunk, True)
            if lic_info != "PLATE_UNK":
                lic_info = lic_info.split()
                lic_state = lic_info[0]
                lic_num = lic_info[1]
            else:
                lic_state = lic_info
                lic_num = lic_info
            lic_exp = getTLOExp(vehicle_chunk)
            vin = getVIN(vehicle_chunk)
            ro_info = getRO(vehicle_chunk,True)
            
            vic_infile += 1
            vic_str = build_entry_str(color,year,make,model,body,lic_state,lic_num,lic_exp,vin,ro_info)
            vehicle_list.append(vic_str)
            color = year = make = model = body = lic_state = lic_num = lic_exp = vin = ro_info = "UNK"
        
    # convert the strings to JSON
    for vic in vehicle_list:
        if bVerbose:
            print(f"process_TLO(): Adding {vic}...")
        res = json.loads(vic)
        vehicle_json.append(res)
        
    # save the vehicle list to a CSV file now
    try:
        keys = vehicle_json[0].keys()
    except IndexError:
        return # No vehicle entries
    fname = fname + ".csv"
    with open(fname, 'w', newline='') as csvout:
        dictwriter = csv.DictWriter(csvout, keys)
        dictwriter.writeheader()
        dictwriter.writerows(vehicle_json)

        
def main():
    file_list = []
    
    # Get my list of PDFs
    for f in os.listdir():
        if f.endswith(".pdf"):
            file_list.append(f)
    
    file_list = sorted(file_list)
    
    for file in file_list:
        reader = PdfReader(file)
        first_page = reader.pages[0].extract_text()
        if "liferaft" in first_page:
            print(f"Liferaft document.")
            process_Life(file)
            continue
        if "INVESTIGATOR PURPOSES" in first_page:
            print(f"TLOxp document.")
            process_TLO(file)
            continue
        else:
            print(f"Unknown origin, skipping {file}.")
            continue
    print(f"Done.")
        
if __name__ == "__main__":

    main()






