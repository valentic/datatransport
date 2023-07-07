##########################################################################
#
#   Cancel messages in a news group
#
#   2022-10-10  Todd Valentic
#               Add header comment block
#               Make a package command
#
##########################################################################

import argparse

from datatransport import newstool 

def main():
    
    parser = argparse.ArgumentParser()

    parser.add_argument('newsgroup')

    parser.add_argument('-s','--server',
                default='localhost',
                help='News server host (default %(default)s)')

    parser.add_argument('-p','--port',
                default=119, type=int,
                help='News server port (default %(default)s)') 

    args = parser.parse_args()

    server = newstool.NewsControl()
    server.set_server(args.server, port=args.port)

    if not server.has_newsgroup(args.newsgroup):
        print(f'Error: newsgroup does not exist: {args.newsgroup}')
        return 1 

    print(f'Canceling messages in {args.newsgroup}') 

    server.cancel_newsgroup(args.newsgroup)
    
    return 0
