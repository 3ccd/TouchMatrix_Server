import connection
import controller
import analyzer
import calibration
from demo import visualizer as vis


if __name__ == "__main__":

    # Sharing Data
    t_frame = connection.TmFrame()

    # create instance
    t_calibration = calibration.Calibration(t_frame)
    t_touch_track = analyzer.ObjTracker()
    t_blob_track = analyzer.ObjTracker()
    t_server = connection.OSCServer(t_frame, "192.168.0.4")
    t_frame_client = connection.FrameTransmitter(ip='192.168.0.2')
    t_obj_client = connection.ObjTransmitter(ip='192.168.0.2')
    t_analyzer = analyzer.Analyzer(t_frame, t_calibration, t_touch_track, t_blob_track)
    t_visualizer = vis.Visualizer((320, 640))
    t_view = controller.TmView(t_analyzer, t_server, t_visualizer, t_frame_client, t_calibration)

    # set draw event callback
    t_visualizer.set_callback(t_frame_client.set_frame)
    t_touch_track.event_callback = t_obj_client.send_message
    t_blob_track.event_callback = t_obj_client.send_message

    # initialize demo contents instance
    # from demo import continuous_lines, turn_table, object_detection, object_scan, ocr, touch_send, synthesizer
    from demo import touch_send
    # demo_lines = continuous_lines.ContinuousLines(t_visualizer)
    # demo_table = turn_table.TurnTable(t_visualizer)
    # demo_detection = object_detection.ObjectDetection(t_visualizer)
    # demo_scan = object_scan.ObjectScan(t_visualizer)
    # demo_graphic = ocr.OCR(t_visualizer)
    demo_touch = touch_send.TouchSend(t_visualizer, t_frame_client)
    # demo_synth = synthesizer.Synthesizer(t_visualizer, t_client)

    # register demo contents
    # t_view.insert_contents(demo_lines)
    # t_view.insert_contents(demo_table)
    # t_view.insert_contents(demo_detection)
    # t_view.insert_contents(demo_scan)
    # t_view.insert_contents(demo_graphic)
    t_view.insert_contents(demo_touch)
    # t_view.insert_contents(demo_synth)

    t_analyzer.start()

    # start gui
    t_view.mainloop()

    t_analyzer.stop()
    t_server.stop()
    t_frame_client.stop()
    t_visualizer.stop()
