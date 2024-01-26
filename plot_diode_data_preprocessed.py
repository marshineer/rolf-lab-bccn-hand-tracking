import json
import argparse
import matplotlib.pyplot as plt
from utils import get_files_containing, load_diode_data, get_block_data
from utils_pipeline import SessionConfig


def plot_diode_data(participant_id: str = None, session_id: str = None) -> None:
    if participant_id is None or session_id is None:
        diode_paths, diode_files = get_files_containing("data/pipeline_data", "diode_sensor.csv")
        for path, file in zip(diode_paths, diode_files):
            participant_id, session_id = file.split("_")[:2]
            diode_df = load_diode_data(participant_id, session_id)
            fig, ax = plt.subplots(1, 1, figsize=(16, 5))
            ax.plot(diode_df.time, diode_df.light_value)
            ax.set_xlabel("Time")
            ax.set_ylabel("Diode Brightness")
            ax.set_title(f"Participant {participant_id}, Session {session_id}", fontsize=20)
            plt.show()
            plt.close()
    else:
        diode_df = load_diode_data(participant_id, session_id)
        fig1, ax1 = plt.subplots(1, 1, figsize=(16, 6))
        ax1.plot(diode_df.time, diode_df.light_value)
        ax1.set_xlabel("Time")
        ax1.set_ylabel("Diode Brightness")
        ax1.set_title(f"Participant {participant_id}, Session {session_id}", fontsize=20)
        plt.show()
        plt.close()

        config_path = f"./data/pipeline_data/{participant_id}/{session_id}/config.json"
        with open(config_path, "r") as fd:
            session_settings = json.load(fd)
            print(session_settings)
            sesssion_config = SessionConfig(**session_settings)
        _ = get_block_data(
            diode_df,
            sesssion_config.diode_threshold,
            sesssion_config.separator_threshold,
            sesssion_config.n_blocks,
            sesssion_config.skip_valid_blocks,
            sesssion_config.extra_apriltag_blocks,
            True,
        )
        plt.close(fig1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-pid", "--participant_id",
        type=str,
        default=None,
        help="Participant ID 'PXX'"
    )
    parser.add_argument(
        "-sid", "--session_id",
        type=str,
        default=None,
        help="Session ID, 'AX' or 'BX'"
    )
    args = parser.parse_args()

    plot_diode_data(args.participant_id, args.session_id)