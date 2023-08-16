
from Transport.InstrumentStatus import Status

def callback(self,init=0,curstatus=None,prevstatus=None,changed=0):

	if init:
		self.log(1,'plugin init called')
		return

	if changed:
		self.log(1,'Callback called: change detected')

