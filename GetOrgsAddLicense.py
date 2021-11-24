# This script, for a given API key, gets every Organisation for that key
# it then allows you to select an org, and either ADD or RENEW licenses for that org
# Mandatory arguments:
# -k <API KEY>      : Your Meraki Dashboard API Key
# Pre requisites:
# Meraki library : pip install meraki : https://developer.cisco.com/meraki/api/#/python/getting-started

import meraki
import logging, sys, getopt

loggingEnabled = True

licensesAdded = []
licensesNotFound = []
licensesAlreadyUsed = []



def main(argv):

    writeToLog("Meraki Library version: ", loggingEnabled)
    writeToLog(meraki.__version__, loggingEnabled)

    try:
        opts, args = getopt.getopt(argv, 'k:')
    except getopt.GetOptError:
        printhelp(argv)
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-k':
            arg_apikey = arg

    # Create Meraki Client Object and initialise
    client = meraki.DashboardAPI(api_key=arg_apikey)

    # things to do
    #1. Get orgs
    #2. Ask user for org
    #3. does entered org exist in list?
    #3.     No return to 2
    #3.5 Check if PDL
    #3.5    Yes, exit with error
    #4. enter comma separated list of licenses
    #5. Check that licenses entered are valid
    #5.     If no, exit with status
    #6. Get current licenses and store
    #7. make API call(s) to add licenses
    #8. Get new licenses to compare


    #1 Get Orgs for given API key
    orgs = client.organizations.getOrganizations()
    writeToLog(orgs, loggingEnabled)

    #2 Ask user for org ID


    print("Please enter the name of the Org to add licenses to. This can be found in the Meraki dashboard under:")
    print("Organization > Settings > Name")
    Org_Name = input("Organization Name, verbatim, please : ")

    writeToLog(type(orgs), loggingEnabled)

    # 3. does entered org exist in list?
    # 3.     No return to 2
    doesOrgNameExist = next(filter(lambda obj: obj.get('name') == Org_Name, orgs), None)
    writeToLog("results of search of entered Org name vs Available Orgs", loggingEnabled)
    writeToLog(doesOrgNameExist, loggingEnabled)

    if doesOrgNameExist == "None":
        print("Entered Org does not exist")
        quit()
    else:
        organization_id = (doesOrgNameExist['id'])
        writeToLog(organization_id, loggingEnabled)

    # 3.5 Check if PDL
    # getOrganizationLicenses() is only available to PDL networks. Therefore, will error with
    # {'errors': ['Organization with ID 800607 does not support per-device licensing']}
    # if a PDL network
    licenses = getLicenses(client, organization_id)
    if not licenses == "fail":
        print("This organaization supports per device licensing, and licenses have to be added manually (for the moment)")
        quit()

    # now that we've checked for PDL, let's proceed

    # 4. enter comma separated list of licenses
    print("Please enter the list of licenses, separated by commas, with no spaces")
    print("IE: Z123-45AB-6C78,Z123-45AB-6C79,Z123-45AB-6C70")
    licensesEntered = input("Press enter after pasting in : ")

    license_list = licensesEntered.split(",")
    writeToLog(license_list,loggingEnabled)

    # check that only alpha has been entered
    # this needs building out to detect the actual input and get the user to re-enter
    for license in license_list:
        if not license.isalpha():
            writeToLog("Non alpha input detected, bork",loggingEnabled)

    # 6. Get current licenses and store
    # may need strengthening if NO licenses at all. Need to check
    licenseOverview = getLicenseOverview(client, organization_id)
    curr_expir_date = licenseOverview["expirationDate"]
    curr_license_counts = licenseOverview["licensedDeviceCounts"]

    try:
        curr_sm_licenses = curr_license_counts["SM"]
    except getopt.GetOptError:
        # no SM licenses so set SM licenses to 0
        curr_sm_licenses = 0

    # 7. make API call(s) to add licenses
    print("Do you want to ADD licenses, or RENEW? ADD is for new SM deployments, or where you need to ADD new devices on top of an existing deployment")
    print("Going from 500 to 700 devices, say.")
    print("RENEW is where you have existing SM licenses and you want to increase their length")
    renewal_type = input("Type ADD or RENEW followed by the ENTER key : ")

    if renewal_type == "RENEW":
        AddOperation = "renew"
    else:
        AddOperation = "addDevices"

    for license in license_list:
        op_data = [{"key": license, "mode": AddOperation}]
        #license_line = client.organizations.claimIntoOrganization(organizationId=organization_id, licenses=op_data)
        license_line = addLicense(client, organization_id, op_data)
        if "not found" in license_line:
            licensesNotFound.append(license)
            writeToLog(op_data, loggingEnabled)
        elif "has already been claimed." in license_line:
            licensesAlreadyUsed.append(license)
            writeToLog(op_data, loggingEnabled)
        else:
            licensesAdded.append(license)

    # 8. Get new licenses to compare
    NEWlicenseOverview = getLicenseOverview(client, organization_id)
    NEW_expir_date = NEWlicenseOverview["expirationDate"]
    NEW_license_counts = NEWlicenseOverview["licensedDeviceCounts"]
    NEW_sm_licenses = NEW_license_counts["SM"]

    print("****************************************************************************")
    print("SUMMARY:")
    print()
    print("Old License count for SM=", end=" ")
    print(curr_sm_licenses)
    print("Old License Co-term expiration date=", end=" ")
    print(curr_expir_date)
    print()
    print("NEW License count for SM=", end=" ")
    print(NEW_sm_licenses)
    print("NEW License Co-term expiration date=", end=" ")
    print(NEW_expir_date)
    print("****************************************************************************")
    print("Licenses Added:")
    print(licensesAdded)
    print("****************************************************************************")
    print("Licenses Not Found:")
    print(licensesNotFound)
    print("****************************************************************************")
    print("Licenses already used:")
    print(licensesAlreadyUsed)

def printhelp():
    # prints help information

    print('This is a script to Get the SM licenses and enrolled devices across multiple organisations.')
    print('')
    print('Mandatory arguments:')
    print(' -k <api key>         : Your Meraki Dashboard API key')


def addLicense(passedClient, passedOrgID, passedOpData):
    try:
        result = passedClient.organizations.claimIntoOrganization(organizationId=passedOrgID, licenses=passedOpData)
    except meraki.APIError as e:
        writeToLog(e, loggingEnabled)
        #error class contains:
        # meraki.APIError.tag
        # meraki.APIError.operation
        # meraki.APIError.status
        # meraki.APIError.reason
        # meraki.APIError.message
        messageList = e.message["errors"]
        result = messageList[0]
    return result

def getLicenseOverview(passedClient, passedOrgID):
    try:
        result = passedClient.organizations.getOrganizationLicensesOverview(organizationId=passedOrgID)
    except meraki.APIError as e:
        writeToLog(e, loggingEnabled)
        result = 'fail'
    return result

def getLicenses(passedClient, passedOrgID):
    try:
        result = passedClient.organizations.getOrganizationLicenses(organizationId=passedOrgID)
    except meraki.APIError as e:
        writeToLog(e, loggingEnabled)
        result = 'fail'
    return result

def getNetworks(passedClient, passedOrgID):
    try:
        networksResult = passedClient.organizations.getOrganizationNetworks(organizationId=passedOrgID)

    except meraki.APIError as e:
        writeToLog(e, loggingEnabled)
        networksResult = 'fail'
    return networksResult


def writeToLog(MessageToLog, toLog):
    if toLog:
        logging.warning(MessageToLog)

def writeToFile(passedFile, messagetoWrite):
    openFileForRead = open(passedFile, 'r')
    fileContents = openFileForRead.read()
    openFileForRead.close()

    openedFile = open(passedFile, 'w')
    openedFile.writelines(fileContents)
    openedFile.writelines('\n')
    openedFile.writelines(messagetoWrite)
    openedFile.close()


if __name__ == '__main__':
    main(sys.argv[1:])
