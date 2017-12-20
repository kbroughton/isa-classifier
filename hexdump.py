""""
 * Created by kbroughton on 11/15/17.
"""
import base64
import binascii
import math
import re


class Hexdump:
    
    def __init__(self, data, options):
        self.hexdump = []
        self.hex = False
        self.options = {
            "container": options.get('container', ''),
            "width": options.get('width', 8),
            "byteGrouping": options.get('byteGrouping', 4),
            "ascii": options.get('ascii', None),
            "lineNumber": options.get('lineNumber', True),
            "endian": options.get('endian', 'big'),
            "html": options.get('html', None),
            "base": options.get('base', 'hexadecimal'),
            "nonPrintable": options.get('nonPrintable', '.'),
            "style": {
            "lineNumberLeft": options['style'].get('lineNumberLeft', ''),
            "lineNumberRight": options['style'].get('lineNumberRight', ':'),
            "hexLeft": options['style'].get('hexLeft', ''),
            "hexRight": options['style'].get('hexRight', ''),
            "hexNull": options['style'].get('hexNull', '00'),
            "stringNull": options['style'].get('stringNull', ' ')
          }
        }
        # What is this for?
        self.options['byteGrouping'] -= 1

        # Base padding
        self.padding = 4
        self.options['base'] = 'hex'
        self.hex = True

        self.setNullPadding(self.padding)

        self.data = re.findall('.{1,' + str(self.options['width']) + '}', data)

        self.nullCount = self.options['width'] - len(self.data[len(self.data) - 1])

        self.hexCounter = 0

        self.stringCounter = 0

        for i in range(len(self.data)):
            tempData = self.process(self.data[i])

            self.hexdump.append({
                'data': tempData['data'],
                'string': tempData['string'],
                'length': len(self.data[i]),
                'missing': self.options['width'] - len(self.data[i])
              })


        self.dump()

    def baseConvert(self, characters):
        pad = ''
        for i in range(len(characters)):
            #        return self.addPadding(characters[i].charCodeAt(0).toString(16), self.padding);
            pad += self.addPadding(binascii.hexlify(str(ord(characters[i]))), self.padding)
        return pad

    
    def dump(self):
        
        self.output = ''
        for i in range(len(self.hexdump)):

            if self.options['lineNumber']:
                tempLineNumberStyle = ''
                tempLineNumberStyle += self.options['style']['lineNumberLeft']

                currentLineCount = (i * self.options['width'])    # .toString(16)
                temLineCount = 8 - currentLineCount
                for j in range(temLineCount):
                    tempLineNumberStyle += '0'

                tempLineNumberStyle += str(currentLineCount)
                tempLineNumberStyle += self.options['style']['lineNumberRight'] + ' '

                if self.options['html']:
                    self.output += '<span id="line-number">'+tempLineNumberStyle+'</span>'
                else:
                    self.output += tempLineNumberStyle



            spacingCount = 0
            breakPoint = math.floor(self.options['width'] / 2)

            self.output += self.options['style']['hexLeft']

            for x in range(len(self.hexdump[i]['data'])):

                if spacingCount == self.options['byteGrouping']:
                    if x == len(self.hexdump[i]['data']) - 1:
                        self.output += self.hexdump[i]['data'][x]
                    else:
                        self.output += self.hexdump[i]['data'][x] + ' '

                    spacingCount = 0
                else:
                    self.output += self.hexdump[i]['data'][x]
                    spacingCount += 1

            self.output += self.options['style']['hexRight']

            self.output += "\n"


        #hexdump_container = document.getElementById(this.options.container)
        #hexdump_container.innerHTML = this.output
        return self.output


    def splitNulls(self, code):
        split = []
        buffer = ""

        if code and len(code) > 2:
            for cc in range(len(code)):
                tempi = cc + 1

                if tempi % 2 == 0:
                    buffer += str(code[cc])
                    split.append(buffer)
                    buffer = ""
                else:
                    buffer += str(code[cc])

        return split


    def process(self, data):
        stringArray = []
        hexArray = []

        for i in range(len(data)):
            if self.options['html']:
                code = self.baseConvert(data[i])

                if self.hex:
                    split = self.splitNulls(code)
                    for var in range(len(split)):
                        hexArray.append('<span data-hex-id="' + self.hexCounter + '">' +
                        split[y] + '</span>')
                else:
                    hexArray.append('<span data-hex-id="' + self.hexCounter + '">' +
                    code + '</span>')



                stringArray.append('<span data-string-id="' + self.hexCounter + '">' +
                         '</span>')

            else:
                code = self.baseConvert(data[i])

                if self.hex:
                    split = self.splitNulls(code)

                    for y in range(len(split)):
                        hexArray.append(split[y])
                else:
                    hexArray.append(code)

            self.hexCounter += 1


        if self.hex:
            splitHexWidth = self.options['width'] * 2
        else:
            splitHexWidth = self.options['width']


        if len(hexArray) < splitHexWidth:
            amount = splitHexWidth - len(hexArray)

            for i in range(amount):
                nullHex = ''

                if self.options['html']:
                    nullHex = '<span data-hex-null="true">' + self.options['style']['hexNull'] + '</span>'
                else:
                    nullHex = self.options['style']['hexNull']

                hexArray.append(nullHex)



        if len(stringArray) < self.options['width']:
            stringAmount = self.options['width'] - len(stringArray)
            for i in range(stringAmount):
                nullString = ''

            if self.options['html']:
                nullString = '<span data-string-null="true">' + self.options['style']['stringNull'] + '</span>'
            else:
                nullString = self.options['style']['stringNull']



        stringArray.append(nullString)



        return { 'data': hexArray, 'string': ''.join(stringArray) }


    def setNullPadding(self, padding):
        hexNull = self.options['style']['hexNull'][0]
        self.options['style']['hexNull'] = ""

        if self.hex:
            padding = padding / 2


        for p in range(padding):
            self.options['style']['hexNull'] += hexNull

    def addPadding(self, ch, padding):
        length = len(str(ch)) 
        pad = ''

        for i in range(padding - length):
            pad += '0'

        if self.options['endian'] == 'big':
            return pad + ch
        else:
            return ch + pad


if __name__ == "__main__":
    binary_data = [u'GAAAABgAAAAAAAAAqAAAAABIDhBHmgJa2g4AAAAAQaAAAD0kAABetxEE/0cCAOJDAAAQIgAAQbAAAF0kAABCoA==',
                   u'AAAAAAABelIABHgaARsNHgAYAAAAGAAAAAAAAACMAAAAAEMOEEGaAl7aDgAAAwDjQwAAPSQAAGGwAABCIAQAQg==',
                   u'AOUBIRjRGdMSYRnUEB9iYRjRMiEyITIhCtMCITJjFtAyISIhYmMA5jIhIiFxUiIhclIiIQtACQAA4AR/Jk/2aQ==',
                   u'g/gCfui4AAAAAOsTSGPQixSVAAAAAIkVAAAAAIPAAYXAfum4AAAAAOsTSGPQD7aSAAAAAIkVAAAAAIPAAYP4AQ==']
    bd = base64.b64decode(binary_data[0])
    hd = Hexdump(bd, {'container': 'binary', 'style': {}})
    hd.output.split('\n')