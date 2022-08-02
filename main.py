import connection
import controller
import analyzer
import calibration
from demo import visualizer as vis
from tracker import ObjTracker


if __name__ == "__main__":

    # Sharing Data
    t_frame = connection.TmFrame()

    # create instance
    t_calibration = calibration.Calibration(t_frame, True)
    t_touch_track = ObjTracker()
    t_blob_track = ObjTracker()
    # t_server = connection.OSCServer(t_frame, "192.168.0.4")
    t_server = connection.SerialServer(t_frame, "/dev/ttyACM0")
    t_frame_client = connection.FrameTransmitter(ip='192.168.0.2')
    t_obj_client = connection.ObjTransmitter(ip='192.168.0.2')
    t_analyzer = analyzer.Analyzer(t_frame, t_calibration, t_touch_track, t_blob_track)
    t_visualizer = vis.Visualizer((320, 640))
    t_view = controller.TmView(t_analyzer, t_server, t_visualizer, t_frame_client, t_calibration)

    # set draw event callback
    t_visualizer.set_callback(t_frame_client.set_frame)
    t_touch_track.set_callback(t_obj_client.send_message)
    t_blob_track.set_callback(t_obj_client.send_message)
    t_analyzer.start()

    # start gui
    t_view.mainloop()

    t_analyzer.stop()
    t_server.stop()
    t_frame_client.stop()
    t_visualizer.stop()
