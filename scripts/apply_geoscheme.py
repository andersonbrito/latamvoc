# -*- coding: utf-8 -*-

import pycountry_convert as pyCountry
import pycountry
import pandas as pd
import argparse
from uszipcode import SearchEngine


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Reformat metadata file by adding column with subcontinental regions based on the UN geo-scheme",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--metadata", required=True, help="Nextstrain metadata file")
    parser.add_argument("--geoscheme", required=True, help="XML file with geographic classifications")
    parser.add_argument("--output", required=True, help="Updated metadata file")
    args = parser.parse_args()

    metadata = args.metadata
    geoscheme = args.geoscheme
    output = args.output

    # path = '/Users/anderson/GLab Dropbox/Anderson Brito/github/latamvoc/'
    # metadata = path + 'pre-analyses/metadata_filtered.tsv'
    # geoscheme = path + 'config/geoscheme.tsv'
    # output = path + 'pre-analyses/metadata_geo.tsv'


    # get ISO alpha3 country codes
    isos = {}
    def get_iso(country):
        global isos
        if country not in isos.keys():
            try:
                isoCode = pyCountry.country_name_to_country_alpha3(country, cn_name_format="default")
                isos[country] = isoCode
            except:
                try:
                    isoCode = pycountry.countries.search_fuzzy(country)[0].alpha_3
                    isos[country] = isoCode
                except:
                    isos[country] = ''
        return isos[country]

    # parse subcontinental regions in geoscheme
    scheme_list = open(geoscheme, "r").readlines()[1:]
    geoLevels = {}
    c = 0
    for line in scheme_list:
        if not line.startswith('\n'):
            id = line.split('\t')[2]
            type = line.split('\t')[0]
            members = line.split('\t')[5].split(',')  # elements inside the subarea

            if type == 'region':
                for country in members:
                    iso = get_iso(country.strip())
                    geoLevels[iso] = id

            # parse subnational regions for countries in geoscheme
            if type == 'country':
                for state in members:
                    if state.strip() not in geoLevels.keys():
                        geoLevels[state.strip()] = id

            # parse subareas for states in geoscheme
            if type == 'location':
                for zipcode in members:
                    if zipcode.strip() not in geoLevels.keys():
                        geoLevels[zipcode.strip()] = id

            for elem in members:
                if elem.strip() not in geoLevels.keys():
                    geoLevels[elem.strip()] = id

    # open metadata file as dataframe
    dfN = pd.read_csv(metadata, encoding='utf-8', sep='\t')
    try:
        dfN.insert(4, 'region', '')
    except:
        pass
    dfN['region'] = dfN['iso'].map(geoLevels) # add 'column' region in metadata
    dfN['subregion'] = ''

    # convert sets of locations into sub-locations
    print('\nApplying geo-schemes...')
    custom_geolevels = {}
    for line in scheme_list:
        if not line.startswith('\n'):
            line = line.strip()
            id = line.split('\t')[2]
            type = line.split('\t')[0]
            members = line.split('\t')[5].split(',')  # elements inside the subarea

            if type == 'subregion':
                for country in members:
                    country = country.strip()
                    custom_geolevels[country] = id

    dfN.fillna('', inplace=True)
    for idx, row in dfN.iterrows():
        country = dfN.loc[idx, 'country']
        division = dfN.loc[idx, 'division']
        region = dfN.loc[idx, 'region']
        # assign sub region
        if region not in ['Central America', 'South America', 'Caribbean']:
            # print(country, region)

            if 'Europe' in dfN.loc[idx, 'region']:
                dfN.loc[idx, 'subregion'] = 'Europe'
            if 'North America' in dfN.loc[idx, 'region']:
                dfN.loc[idx, 'subregion'] = 'North America'
            else:
                if dfN.loc[idx, 'subregion'] == '':
                    dfN.loc[idx, 'subregion'] = 'Other region'

        if region in ['Central America', 'South America', 'Caribbean'] and dfN.loc[idx, 'subregion'] == '':
            if country == 'Brazil':
                if division in custom_geolevels.keys():
                    dfN.loc[idx, 'subregion'] = custom_geolevels[division]
                else:
                    dfN.loc[idx, 'subregion'] = 'Other region'
                    print('\t- ' + division + ' not found in geoscheme.')
            else:
                if country in custom_geolevels.keys():
                    dfN.loc[idx, 'subregion'] = custom_geolevels[country]
                else:
                    dfN.loc[idx, 'subregion'] = 'Other region'
                    print('\t- ' + country + ' not found in geoscheme.')
        print(dfN.loc[idx, 'subregion'], country, division)

        # # divide country into subnational regions
        # division = dfN.loc[idx, 'division']
        # if division not in ['', 'unknown']:
        #     if division in custom_geolevels.keys():
        #         dfN.loc[idx, 'country'] = custom_geolevels[dfN.loc[idx, 'country']]

    print(custom_geolevels)

    dfN = dfN.drop_duplicates(subset=['strain'])
    dfN.to_csv(output, sep='\t', index=False)

print('\nMetadata file successfully reformatted applying geo-scheme!\n')
