#!/usr/bin/env python

from Transport      import ProcessClient
from Transport      import NewsPostMixin
from datetime       import datetime

import sys
import random
import ConfigParser
import StringIO
import pytz

class DataSource(ProcessClient,NewsPostMixin):

    def __init__(self,argv):
        ProcessClient.__init__(self,argv)
        NewsPostMixin.__init__(self)

        self.pollrate   = self.getDeltaTime('rate',60)
        self.sites      = self.get('sites','').split()
        self.config     = ConfigParser.ConfigParser()

        self.config.add_section('Temperature')
        self.config.add_section('Voltage')

    def run(self):

        internal    = 20
        external    = 40

        genseta     = 110
        gensetb     = 110

        while self.running:

            for site in self.sites:

                internal    += random.uniform(-2,2)
                external    += random.uniform(-2,2)
                genseta     += random.uniform(-1,1)
                gensetb     += random.uniform(-1,1)

                self.config.set('Temperature','Internal',internal)
                self.config.set('Temperature','External',external)
                self.config.set('Voltage','GeneratorA',genseta)
                self.config.set('Voltage','GeneratorB',gensetb)

                buffer = StringIO.StringIO()
                self.config.write(buffer)
                msg = buffer.getvalue()

                now = datetime.now(pytz.utc)
                headers = {'X-Site':site}

                self.newsPoster.postText(msg,date=now,headers=headers)

            self.log.info('Posted data samples')

            self.wait(self.pollrate)

if __name__ == '__main__':
    DataSource(sys.argv).run()

