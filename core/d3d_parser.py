import configparser

class MduParser:
    @staticmethod
    def read_mdu(file_path):
        parser = configparser.ConfigParser(allow_no_value=True)
        parser.optionxform = str 
        parser.read(file_path, encoding='utf-8')
        return parser

    @staticmethod
    def write_mdu(parser, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            parser.write(f)