import Main as mm
import Globals as gb
import LoggingHD as lg



print ("initiating")
lg.setup_logging()
lg.logger.info("logger initiated")



#initiating the program
gb.set_public_current_client(0)
lg.logger.info("Program initiated")


lg.logger.info("Starting Program")
mm.main()