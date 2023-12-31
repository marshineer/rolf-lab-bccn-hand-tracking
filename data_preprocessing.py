import os
import cv2
import time
import numpy as np
import pandas as pd
from pathlib import Path
from utils import get_files_containing


def concatenate_video_data() -> None:
    """Concatenates all two part session videos."""

    # Get the video and gaze files and group by session
    video_paths, video_files = get_files_containing("data/original_data/", ".mp4", "block")
    video_parts = {path: [] for path in set(video_paths)}
    for dirpath, file in zip(video_paths, video_files):
        video_parts[dirpath].append(file)
    gaze_paths, gaze_files = get_files_containing("data/original_data/", "gaze_positions")
    gaze_parts = {path: [] for path in set(gaze_paths)}
    for dirpath, file in zip(gaze_paths, gaze_files):
        gaze_parts[dirpath].append(file)

    # For each session, preprocess the gaze data and concatenate any multi-part files
    for dirpath, file_list in gaze_parts.items():
        session_gaze_dfs = []
        for i, file in enumerate(file_list):
            participant_id, session_id = dirpath.split("/")[-2:]
            new_dirpath = f"data/pipeline_data/{participant_id}/{session_id}"
            Path(new_dirpath).mkdir(parents=True, exist_ok=True)
            new_filename = f"{participant_id}_{session_id}_video_time.csv"
            gaze_df = preprocess_gaze_data(os.path.join(dirpath, file), False)
            if i > 0:
                time_diff = session_gaze_dfs[-1].time.diff().median()
                gaze_df['time'] += session_gaze_dfs[-1].time.iloc[-1] + time_diff
                gaze_df.video_frame += session_gaze_dfs[-1].video_frame.iloc[-1] + 1
            session_gaze_dfs.append(gaze_df)
        combined_gaze_df = pd.concat(session_gaze_dfs, ignore_index=True)
        combined_gaze_df.time.to_csv(os.path.join(new_dirpath, new_filename), index=False)

    # For each session, preprocess the gaze data and concatenate any multi-part files
    for dirpath, file_list in video_parts.items():
        print(f"Processing videos: {file_list}")
        participant_id, session_id = file_list[0].split(".")[0].split("_")[:2]
        new_dirpath = f"data/pipeline_data/{participant_id}/{session_id}"
        Path(new_dirpath).mkdir(parents=True, exist_ok=True)
        new_filename = f"{participant_id}_{session_id}.mp4"
        if len(file_list) > 1 and not os.path.exists(os.path.join(new_dirpath, new_filename)):
            # Initialize a new video writer
            vcap = cv2.VideoCapture(os.path.join(dirpath, file_list[0]))
            width = int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = vcap.get(cv2.CAP_PROP_FPS)
            codec = int(vcap.get(cv2.CAP_PROP_FOURCC))
            vcap.release()
            cv2.destroyAllWindows()
            new_video = cv2.VideoWriter(os.path.join(new_dirpath, new_filename), codec, fps, (width, height))

            # Write the video parts to a single file
            video_frame_reported = 0
            video_frame_cnt = 0
            run_time_t0 = time.time()
            for file in file_list:
                vcap = cv2.VideoCapture(os.path.join(dirpath, file))
                video_frame_reported += int(vcap.get(cv2.CAP_PROP_FRAME_COUNT))
                while vcap.isOpened():
                    # Read the next frame
                    ret, frame = vcap.read()
                    if not ret:
                        break
                    video_frame_cnt += 1
                    new_video.write(frame)
            print(f"It took {time.time() - run_time_t0:0.2f} seconds to concatenate videos")
            assert video_frame_cnt == video_frame_reported
        else:
            os.rename(os.path.join(dirpath, file_list[0]), os.path.join(new_dirpath, file_list[0]))


def preprocess_diode_data() -> None:
    """Preprocesses the light diode sensor data for all two_part_videos and sessions.

    The light diode sensor data is renamed and sessions with multiple files are concatenated."""

    # Get the light diode files and group by session
    diode_paths, diode_files = get_files_containing("data/original_data/", "light.csv")
    file_parts = {path: [] for path in set(diode_paths)}
    for dirpath, file in zip(diode_paths, diode_files):
        file_parts[dirpath].append(file)

    # For each session, preprocess the light diode data and concatenate any multi-part files
    for dirpath, file_list in file_parts.items():
        session_diode_dfs = []
        for i, file in enumerate(file_list):
            participant_id, session_id = file.split("_")[:2]
            new_dirpath = f"data/pipeline_data/P{participant_id}/{session_id}"
            Path(new_dirpath).mkdir(parents=True, exist_ok=True)
            new_filename = f"P{participant_id}_{session_id}_diode_sensor.csv"
            diode_df = format_diode_df(os.path.join(dirpath, file))
            if i > 0:
                time_diff = session_diode_dfs[-1].time.diff().median()
                diode_df.time += session_diode_dfs[-1].time.iloc[-1] + time_diff
            session_diode_dfs.append(diode_df)
        combined_diode_df = pd.concat(session_diode_dfs, ignore_index=True)
        combined_diode_df.to_csv(os.path.join(new_dirpath, new_filename), index=False)


def format_diode_df(diode_path: str) -> pd.DataFrame:
    """Format the light diode sensor data of a particular session.

    Parameters
        diode_path (str): relative path to diode data file
        diode_suffix (str): additional filename identifier

    Returns
        diode_df (pd.DataFrame): processed diode data
    """

    diode_df = pd.read_csv(diode_path, usecols=[' timestamp', ' light_value'])
    diode_df.columns = ['time', 'light_value']
    diode_df.time = diode_df.time - diode_df.time.iloc[0]
    return diode_df


def preprocess_gaze_data(gaze_path: str, plot_result: bool) -> pd.DataFrame:
    """Preprocesses the gaze time data.

    The gaze data world_index corresponds to the video frame number, so the gaze data time
    can be used to determine the timestamps of the video frames.

    Parameters
        gaze_path (str): relative path to gaze data file
        plot_result (bool): whether to display plots as visual checks on the process

    Returns
        gaze_df (pd.DataFrame): gaze positiona and video frame timestamp data
    """

    gaze_df = pd.read_csv(gaze_path, usecols=['world_timestamp', 'world_index'])
    column_types = {'time': float, 'video_frame': int}
    gaze_df.columns = ['time', 'video_frame']
    gaze_df.time = gaze_df.time - gaze_df.time.iloc[0]
    gaze_df = gaze_df.drop_duplicates('video_frame').reset_index(drop=True)
    if gaze_df.video_frame.iloc[0] != 0:
        dt_median = gaze_df.time.diff().median()
        gaze_df.time = gaze_df.time + gaze_df.video_frame.iloc[0] * dt_median
        gaze_df.loc[-0.5] = [0., 0]
        gaze_df = gaze_df.sort_index().reset_index(drop=True)
    gaze_df = add_missing_gaze_rows(gaze_df, plot_result)
    gaze_df = gaze_df.astype(column_types)
    return gaze_df


def add_missing_gaze_rows(gaze_data: pd.DataFrame, plot_result: bool) -> pd.DataFrame:
    """Adds missing time frames to gaze data.

    Interpolates the times of missing video frames. If the number of frames missing is less
    than the number of time steps, the missing time steps are left at the end of the frame gap.
    These time steps are handled by another method.

    Note: The gaze data is related to the mp4 video data by the video_frame column. This data
    is important for determining the video time, since the gaze times should be accurate, and
    the video frames have no timestamp associated with them. The only way to calculate the video
    time from an mp4 is by counting the frames, which is unreliable if frames are dropped.

    This method assumes that each video frame in the actual mp4 file corresponds to a value in the
    'video_frame' column of the gaze data. Therefore, the values in this column should be continuous.

    Paramters
        gaze_data (pd.DataFrame): original gaze data with columns [time, video_frame]
        plot_result (bool): whether to plot the results as a manual check of the interpolation

    Returns
        gaze_data_updated (pd.DataFrame): gaze data updated with missing video frames
    """

    # Find the median time step in the data
    dt_median = gaze_data.time.diff().median()
    print(f"Median dt: {dt_median}")

    # Interpolate missing frames in gaze data
    gaze_data_updated = gaze_data.copy()
    gaze_data_old = gaze_data.copy()
    gap_inds_old = list(gaze_data_updated.index[gaze_data_updated.video_frame.diff() > 1])
    gap_inds_updated = []
    gap_lens = []

    # While there are still missing rows in the gaze data
    while list(gaze_data_updated.index[gaze_data_updated.video_frame.diff() > 1]):
        # Calculate frame indices
        first_frame_ind = gaze_data_updated.index[gaze_data_updated.video_frame.diff() > 1][0] - 1
        frame_prev = gaze_data_updated.iloc[first_frame_ind]
        frame_next = gaze_data_updated.iloc[first_frame_ind + 1]
        n_missing_frames = round(frame_next.video_frame - frame_prev.video_frame)
        gap_inds_updated.append(first_frame_ind)
        gap_lens.append(n_missing_frames)

        # Calculate frame time information
        time_diff = frame_next.time - frame_prev.time
        n_dts = round(time_diff / dt_median)

        # Calculate the number of dropped frames
        n_dropped_frames = n_dts - n_missing_frames

        # Calculate the number of rows that must be inserted
        n_new_times = n_dts - n_dropped_frames

        # Insert rows into the DataFrame at the proper frame index
        new_df_locs = np.arange(frame_prev.video_frame, frame_prev.video_frame + 1, 1 / n_new_times)[1:]
        new_times = np.arange(frame_prev.time, frame_next.time, dt_median)[1:n_new_times]
        for i, (loc, t) in enumerate(zip(new_df_locs, new_times)):
            gaze_data_updated.loc[loc] = [t, frame_prev.video_frame + i + 1]
        gaze_data_updated = gaze_data_updated.sort_index().reset_index(drop=True)

    # Check after insertion that the number of frames equals the last frame index
    assert len(gaze_data_updated) == int(gaze_data.video_frame.iloc[-1] + 1)

    # Check the interpolation
    if plot_result:
        for ind1, ind2, length in zip(gap_inds_old, gap_inds_updated, gap_lens):
            # Before adding frames
            print(gaze_data_old.iloc[ind1 - 2:ind1 + 2])
            # After adding frames
            print(gaze_data_updated.iloc[ind2 - 2:ind2 + length + 2])
            print()

    return gaze_data_updated


def separate_diode_blocks(
        diode_df: pd.DataFrame,
        apriltag_threshold: int,
        new_block_threshold: int = None,
) -> list[pd.DataFrame]:
    """Separates the diode data into experimental blocks.

    Since blocks tend to be divided by relatively high diode light values, these 'new block' threshold
    crossings can be used to roughly separate the experimental blocks. These blocks are then trimmed to
    begin at the onset of the first of five AprilTags, and end at the onset of the next 'new block' threshold
    crossing.

    This method relies on assuming the pattern of five AprilTags begin a block, and that there is a high
    diode value separating each block, since the exact number of trials in a block is variable. It also
    assumes that there is a high diode value before the first block, and following the last.

    Note: the blocks contain more data here than in their lengths

    Parameters
        diode_df (pd.DataFrame): raw light diode data
        apriltag_threshold (int): light diode threshold for signalling the presence of an AprilTag
        new_block_threshold (int): light diode threshold for signalling a new block

    Returns
        block_list (list[pd.DataFrame]): light diode data separated into individual blocks
    """

    # Find light diode values that indicate a new block begins
    light_values = diode_df.light_value.to_numpy('int', copy=True)
    # TODO: there are many potential types of conditions to handle
    #  1. DONE - High values exist and everything is good (eg. P17-A1)
    #  2. High values exist but can only be used for block end times (eg. P05-A2)
    #      -> Must use AprilTag sets to identify block starts
    #  3. High values exist but can only be used for block start times/first AprilTag identification (eg. none yet)
    #  4. No high values exist (eg. P02-A1)
    #      -> Must use AprilTag sets to identify block starts
    if new_block_threshold is not None:
        new_block_crossings = np.where(np.diff(light_values > new_block_threshold))[0] + 1
        # # TODO: need some kind of check in case the light diode starts with a high value
        # # I think this works
        # if light_values[0] > self.diode_threshold_new_block:
        #     new_block_crossings = np.insert(new_block_crossings, 0, 0)
        # TODO: check if light diode value always goes high at the end of a session (required for step below)
        cross_down_inds = new_block_crossings[1::2]
        # block_end_inds = new_block_crossings[2::2]
        # Find light diode indices where new blocks begin (i.e. onset of first AprilTag)
        apriltag_event_crossings = np.where(np.diff(light_values > apriltag_threshold))[0] + 1
        # The line below is a little confusing, but it basically finds the first threshold crossing after the
        #  downward crossing of a high value threshold. This should be the onset of the first AprilTag in a block.
        first_apriltag_inds_event_crossings = np.searchsorted(apriltag_event_crossings, cross_down_inds) + 1
        first_apriltag_inds_time = apriltag_event_crossings[first_apriltag_inds_event_crossings]
    else:
        # Find light diode indices where new blocks begin (i.e. onset of first AprilTag)
        n_apriltag_set = 9
        all_crossings = np.where(np.diff(light_values > apriltag_threshold))[0] + 1
        diode_time = diode_df.time.to_numpy('float', copy=True)
        first_apriltag_inds_time = []
        # first_event_inds_time = []
        for ind0, ind1 in zip(all_crossings[:-n_apriltag_set], all_crossings[n_apriltag_set:]):
            if 9.0 < (diode_time[ind1] - diode_time[ind0]) < 9.2:
                first_apriltag_inds_time.append(ind0)
        # for i, ind0 in enumerate(all_crossings[:-n_apriltag_set]):
        #     ind1 = all_crossings[n_apriltag_set + i]
        #     ind_event = all_crossings[n_apriltag_set + i + 1]
        #     if 9.0 < (diode_time[ind1] - diode_time[ind0]) < 9.2:
        #         first_apriltag_inds_time.append(ind0)
        #         first_event_inds_time.append(ind_event)
        #
        # # Find light diode indices after the last event of the block
        # block_end_inds = []
        # for i, ind in enumerate(first_apriltag_inds_time):
        #     ind1 = first_apriltag_inds_time[i + 1] if i < len(first_apriltag_inds_time) else np.inf
        #     event_inds = all_crossings[(all_crossings > ind) & (all_crossings < ind1)]
        #     event_times =

    # print(first_apriltag_inds_time)

    # Separate data into blocks
    block_list = []
    for i, ind1 in enumerate(first_apriltag_inds_time):
        if i < len(first_apriltag_inds_time) - 1:
            ind2 = first_apriltag_inds_time[i + 1]
            block = diode_df.iloc[ind1:ind2, :]
        else:
            block = diode_df.iloc[ind1:, :]
        block_time = block.time.to_numpy('float', copy=True)
        block_time -= block_time[0]
        block.loc[:, 'time'] = block_time
        block.reset_index(drop=True, inplace=True)
        # block_list.append(block.iloc[:block_end_inds[i], :])
        block_list.append(block)

    return block_list


def get_event_times(
        block_list: list,
        event_threshold: int,
        new_block_threshold: int = None,
) -> tuple[list[np.ndarray], list[float]]:
    """Extracts the event onset times.

    These times are used to check the synchronization between the video and diode data.

    Parameters
        block_list (list[pd.DataFrame]): light diode data, separated into individual blocks
        event_threshold (int): light diode threshold for signalling event onsets
        new_block_threshold (int): light diode threshold for signalling a new block

    Returns
        event_onsets (list[np.ndarray]): event onset times for each block
        block_durations (list[float]): duration of each block
    """

    event_times = []
    block_durations = []
    first_event_ind = 10
    for i, block in enumerate(block_list):
        # Zero the block time
        block_time = block.time.to_numpy('float', copy=True)

        # Get event onset indices
        light_values = block.light_value.to_numpy('int', copy=True)
        all_event_inds = np.where(np.diff(light_values > event_threshold))[0] + 1

        # Get event onset times
        if new_block_threshold is not None:
            last_ind = -2 if i < (len(block_list) - 1) else -1
            event_onset_inds = all_event_inds[first_event_ind:last_ind:2]
            event_times.append(block_time[event_onset_inds])
            block_durations.append(block_time[all_event_inds[last_ind]])
        else:
            # TODO: this is a sloppy way to end the block (is there a better way?)
            #  - at least figure out what number to multiple it by. maybe Clara has some stats.
            event_onset_inds = all_event_inds[first_event_ind::2]
            event_times.append(block_time[event_onset_inds])
            avg_trial_len = np.mean(np.diff(event_times[-1]))
            block_durations.append(event_times[-1][-1] + 0.7 * avg_trial_len)

    return event_times, block_durations


if __name__ == '__main__':
    concatenate_video_data()
    preprocess_diode_data()
