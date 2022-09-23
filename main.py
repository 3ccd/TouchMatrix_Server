import connection
import controller
import analyzer
import calibration
from demo import visualizer as vis
from tracker import ObjTracker

import json


def load_setting():
    with open('./settings.json') as f:
        df = json.load(f)

    return df


if __name__ == "__main__":

    # Load Settings
    param = load_setting()

    # Sharing Data
    t_frame = connection.TmFrame()

    # create instance
    t_calibration = calibration.Calibration(t_frame, False)
    t_touch_track = ObjTracker()
    t_blob_track = ObjTracker()
    # t_server = connection.OSCServer(t_frame, "192.168.0.4")
    t_server = connection.SerialServer(t_frame, param["connection"]["sensor_addr"],
                                       baud=403200)
    t_frame_client = connection.FrameTransmitter(ip='192.168.0.2')
    t_obj_client = connection.ObjTransmitter(ip='192.168.0.2')
    t_analyzer = analyzer.Analyzer(t_calibration, t_touch_track, t_blob_track)
    t_view = controller.TmView(t_analyzer, t_server, t_frame_client, t_calibration, t_frame)

    # set draw event callback
    t_touch_track.set_callback(t_obj_client.send_message)
    t_blob_track.set_callback(t_obj_client.send_message)
    t_analyzer.start()

    t_obj_client.start_client()

    # start gui
    t_view.mainloop()

    t_analyzer.stop()
    t_server.stop()
    t_frame_client.stop()
