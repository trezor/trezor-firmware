"""
Battery Dataset Manager

A class to organize and manage battery profile CSV files with hierarchical structure:
battery_id -> temperature -> battery_mode -> mode_phase -> timestamp_id -> data

File naming convention: <battery_id>.<timestamp_id>.<battery_mode>.<mode_phase>.<temperature>.csv
"""

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .battery_profile import load_battery_profile


class BatteryDataset:
    """
    A class to manage battery profile datasets with hierarchical organization.

    Structure: battery_id -> temperature -> battery_mode -> mode_phase -> timestamp_id -> data
    """

    def __init__(self, dataset_path: Union[str, Path], load_data: bool = True):
        """
        Initialize the battery dataset.

        Args:
            dataset_path: Path to directory containing CSV files or glob pattern
            load_data: Whether to load CSV data immediately or just catalog files
        """
        self.dataset_path = Path(dataset_path)
        self.load_data = load_data

        # Create nested defaultdict structure: battery -> temperature -> mode -> phase -> timestamp -> data
        self._data = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
        )

        # Store file metadata for each entry
        self._file_metadata = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
        )

        # Statistics
        self._stats = {
            "total_files": 0,
            "loaded_files": 0,
            "skipped_files": 0,
            "error_files": 0,
        }

        # Dataset hash (will be calculated after loading)
        self._dataset_hash = None

        # Load the dataset
        self._load_dataset()

    def _parse_filename(self, file_path: Path) -> Optional[Dict[str, str]]:
        """
        Parse filename according to the convention:
        <battery_id>.<timestamp_id>.<battery_mode>.<mode_phase>.<temperature>.csv

        Args:
            file_path: Path to the CSV file

        Returns:
            Dictionary with parsed components or None if parsing fails
        """
        parts = file_path.stem.split(".")

        if len(parts) < 5:
            return None

        return {
            "battery_id": parts[0],
            "timestamp_id": parts[1],
            "battery_mode": parts[2],
            "mode_phase": parts[3],
            "temperature": parts[4],
            "file_path": file_path,
            "file_name": file_path.name,
        }

    def _load_dataset(self):
        """Load all CSV files from the dataset path and organize them."""

        # Handle both directory paths and glob patterns
        if self.dataset_path.is_dir():
            csv_files = list(self.dataset_path.glob("*.csv"))
        else:
            # Assume it's a glob pattern
            csv_files = list(self.dataset_path.parent.glob(self.dataset_path.name))

        print(f"Found {len(csv_files)} CSV files to process...")

        for file_path in csv_files:
            self._stats["total_files"] += 1

            # Parse filename
            file_info = self._parse_filename(file_path)
            if file_info is None:
                print(f"WARNING: Could not parse filename: {file_path.name}")
                self._stats["skipped_files"] += 1
                continue

            battery_id = file_info["battery_id"]
            timestamp_id = file_info["timestamp_id"]
            battery_mode = file_info["battery_mode"]
            mode_phase = file_info["mode_phase"]
            temperature = file_info["temperature"]

            # Skip files with 'done' phase
            if mode_phase == "done":
                print(f"SKIPPING: {file_path.name} - phase 'done'")
                self._stats["skipped_files"] += 1
                continue

            # Store file metadata
            self._file_metadata[battery_id][temperature][battery_mode][mode_phase][
                timestamp_id
            ] = file_info

            # Load data if requested
            if self.load_data:
                try:
                    data = load_battery_profile(file_path)
                    self._data[battery_id][temperature][battery_mode][mode_phase][
                        timestamp_id
                    ] = data
                    self._stats["loaded_files"] += 1
                except Exception as e:
                    print(f"ERROR loading {file_path.name}: {e}")
                    self._stats["error_files"] += 1
            else:
                # Store file path for lazy loading
                self._data[battery_id][temperature][battery_mode][mode_phase][
                    timestamp_id
                ] = file_path
                self._stats["loaded_files"] += 1

        print(f"Dataset loaded: {self._stats}")

        # Calculate dataset hash after loading
        self._dataset_hash = self._calculate_dataset_hash()

    def _calculate_dataset_hash(self) -> str:
        """
        Calculate an 8-character hash that uniquely identifies the dataset content
        based on all file names in the dataset.

        Returns:
            8-character hexadecimal hash string that uniquely identifies the dataset
        """
        # Collect all file names from the dataset
        all_file_names = []

        for battery_id in self._data:
            for temperature in self._data[battery_id]:
                for battery_mode in self._data[battery_id][temperature]:
                    for mode_phase in self._data[battery_id][temperature][battery_mode]:
                        for timestamp_id in self._data[battery_id][temperature][
                            battery_mode
                        ][mode_phase]:
                            # Get file info to extract the original filename
                            file_info = self._file_metadata[battery_id][temperature][
                                battery_mode
                            ][mode_phase][timestamp_id]
                            if file_info and "file_name" in file_info:
                                all_file_names.append(file_info["file_name"])

        # Sort file names for deterministic hash generation
        all_file_names.sort()

        # Create a single string from all file names
        combined_names = "\n".join(all_file_names)

        # Generate SHA256 hash and truncate to 8 characters
        hash_object = hashlib.sha256(combined_names.encode("utf-8"))
        full_hash = hash_object.hexdigest()

        # Return first 8 characters of the hash
        return full_hash[:8]

    def get_dataset_hash(self) -> str:
        """
        Get the 8-character hash that uniquely identifies the dataset content.

        Returns:
            8-character hexadecimal hash string
        """
        return self._dataset_hash

    def get_battery_ids(self) -> List[str]:
        """Get list of all battery IDs in the dataset."""
        return sorted(list(self._data.keys()))

    def get_temperatures(self, battery_id: str) -> List[str]:
        """Get list of all temperatures for a given battery."""
        if battery_id not in self._data:
            return []
        return sorted(list(self._data[battery_id].keys()))

    def get_battery_modes(self, battery_id: str, temperature: str) -> List[str]:
        """Get list of all battery modes for a given battery and temperature."""
        if battery_id not in self._data or temperature not in self._data[battery_id]:
            return []
        return sorted(list(self._data[battery_id][temperature].keys()))

    def get_mode_phases(
        self, battery_id: str, temperature: str, battery_mode: str
    ) -> List[str]:
        """Get list of all mode phases for a given battery, temperature, and mode."""
        if (
            battery_id not in self._data
            or temperature not in self._data[battery_id]
            or battery_mode not in self._data[battery_id][temperature]
        ):
            return []
        return sorted(list(self._data[battery_id][temperature][battery_mode].keys()))

    def get_timestamp_ids(
        self, battery_id: str, temperature: str, battery_mode: str, mode_phase: str
    ) -> List[str]:
        """Get list of all timestamp IDs for a given battery, temperature, mode, and phase."""
        if (
            battery_id not in self._data
            or temperature not in self._data[battery_id]
            or battery_mode not in self._data[battery_id][temperature]
            or mode_phase not in self._data[battery_id][temperature][battery_mode]
        ):
            return []
        return sorted(
            list(self._data[battery_id][temperature][battery_mode][mode_phase].keys())
        )

    def get_all_timestamps_for_battery_temp(
        self, battery_id: str, temperature: str
    ) -> List[str]:
        """
        Get all available timestamps for a given battery_id and temperature
        across all modes and phases.

        Args:
            battery_id: The battery identifier
            temperature: The temperature value (as string)

        Returns:
            Sorted list of unique timestamp IDs found across all modes and phases
        """
        if battery_id not in self._data or temperature not in self._data[battery_id]:
            return []

        all_timestamps = set()

        for battery_mode in self._data[battery_id][temperature]:
            for mode_phase in self._data[battery_id][temperature][battery_mode]:
                timestamps = self._data[battery_id][temperature][battery_mode][
                    mode_phase
                ].keys()
                all_timestamps.update(timestamps)

        return sorted(list(all_timestamps))

    def get_data(
        self,
        battery_id: str,
        temperature: str,
        battery_mode: str,
        mode_phase: str,
        timestamp_id: str,
    ):
        """
        Get data for specific battery profile.

        Returns:
            Loaded data array or None if not found
        """
        try:
            data = self._data[battery_id][temperature][battery_mode][mode_phase][
                timestamp_id
            ]

            # If lazy loading (data is still a file path), load it now
            if isinstance(data, Path):
                loaded_data = load_battery_profile(data)
                # Cache the loaded data
                self._data[battery_id][temperature][battery_mode][mode_phase][
                    timestamp_id
                ] = loaded_data
                return loaded_data

            return data
        except KeyError:
            return None

    def get_file_info(
        self,
        battery_id: str,
        temperature: str,
        battery_mode: str,
        mode_phase: str,
        timestamp_id: str,
    ) -> Optional[Dict]:
        """Get file metadata for specific battery profile."""
        try:
            return self._file_metadata[battery_id][temperature][battery_mode][
                mode_phase
            ][timestamp_id]
        except KeyError:
            return None

    def filter(
        self,
        battery_ids: Optional[List[str]] = None,
        temperatures: Optional[List[str]] = None,
        battery_modes: Optional[List[str]] = None,
        mode_phases: Optional[List[str]] = None,
        timestamp_ids: Optional[List[str]] = None,
    ) -> "BatteryDataset":
        """
        Create a filtered copy of the dataset.

        Args:
            battery_ids: List of battery IDs to include (None = all)
            temperatures: List of temperatures to include (None = all)
            battery_modes: List of battery modes to include (None = all)
            mode_phases: List of mode phases to include (None = all)
            timestamp_ids: List of timestamp IDs to include (None = all)

        Returns:
            New BatteryDataset instance with filtered data
        """

        # Create new instance
        filtered_dataset = BatteryDataset.__new__(BatteryDataset)
        filtered_dataset.dataset_path = self.dataset_path
        filtered_dataset.load_data = self.load_data
        filtered_dataset._data = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
        )
        filtered_dataset._file_metadata = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
        )

        # Inherit dataset hash
        filtered_dataset._dataset_hash = self._dataset_hash

        filtered_dataset._stats = {
            "total_files": 0,
            "loaded_files": 0,
            "skipped_files": 0,
            "error_files": 0,
        }

        # Apply filters
        for battery_id in self._data:
            if battery_ids and battery_id not in battery_ids:
                continue

            for temperature in self._data[battery_id]:
                if temperatures and temperature not in temperatures:
                    continue

                for battery_mode in self._data[battery_id][temperature]:
                    if battery_modes and battery_mode not in battery_modes:
                        continue

                    for mode_phase in self._data[battery_id][temperature][battery_mode]:
                        if mode_phases and mode_phase not in mode_phases:
                            continue

                        for timestamp_id in self._data[battery_id][temperature][
                            battery_mode
                        ][mode_phase]:
                            if timestamp_ids and timestamp_id not in timestamp_ids:
                                continue

                            # Copy data and metadata
                            filtered_dataset._data[battery_id][temperature][
                                battery_mode
                            ][mode_phase][timestamp_id] = self._data[battery_id][
                                temperature
                            ][
                                battery_mode
                            ][
                                mode_phase
                            ][
                                timestamp_id
                            ]
                            filtered_dataset._file_metadata[battery_id][temperature][
                                battery_mode
                            ][mode_phase][timestamp_id] = self._file_metadata[
                                battery_id
                            ][
                                temperature
                            ][
                                battery_mode
                            ][
                                mode_phase
                            ][
                                timestamp_id
                            ]
                            filtered_dataset._stats["total_files"] += 1
                            filtered_dataset._stats["loaded_files"] += 1

        return filtered_dataset

    def get_data_list(
        self,
        battery_ids: Optional[List[str]] = None,
        temperatures: Optional[List[str]] = None,
        battery_modes: Optional[List[str]] = None,
        mode_phases: Optional[List[str]] = None,
        timestamp_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get a list of data entries that match the filtering criteria.

        Args:
            battery_ids: List of battery IDs to include (None = all)
            temperatures: List of temperatures to include (None = all)
            battery_modes: List of battery modes to include (None = all)
            mode_phases: List of mode phases to include (None = all)
            timestamp_ids: List of timestamp IDs to include (None = all)

        Returns:
            List of dictionaries, each containing:
            - 'battery_id': str
            - 'temperature': str
            - 'battery_mode': str
            - 'mode_phase': str
            - 'timestamp_id': str
            - 'data': loaded data object
            - 'file_info': file metadata dict
        """
        result_list = []

        # Apply filters and collect data
        for battery_id in self._data:
            if battery_ids and battery_id not in battery_ids:
                continue

            for temperature in self._data[battery_id]:
                if temperatures and temperature not in temperatures:
                    continue

                for battery_mode in self._data[battery_id][temperature]:
                    if battery_modes and battery_mode not in battery_modes:
                        continue

                    for mode_phase in self._data[battery_id][temperature][battery_mode]:
                        if mode_phases and mode_phase not in mode_phases:
                            continue

                        for timestamp_id in self._data[battery_id][temperature][
                            battery_mode
                        ][mode_phase]:
                            if timestamp_ids and timestamp_id not in timestamp_ids:
                                continue

                            # Get data and file info
                            data = self.get_data(
                                battery_id,
                                temperature,
                                battery_mode,
                                mode_phase,
                                timestamp_id,
                            )
                            file_info = self.get_file_info(
                                battery_id,
                                temperature,
                                battery_mode,
                                mode_phase,
                                timestamp_id,
                            )

                            result_list.append(
                                {
                                    "battery_id": battery_id,
                                    "temperature": temperature,
                                    "battery_mode": battery_mode,
                                    "mode_phase": mode_phase,
                                    "timestamp_id": timestamp_id,
                                    "data": data,
                                    "file_info": file_info,
                                }
                            )

        return result_list

    def get_data_only(
        self,
        battery_ids: Optional[List[str]] = None,
        temperatures: Optional[List[str]] = None,
        battery_modes: Optional[List[str]] = None,
        mode_phases: Optional[List[str]] = None,
        timestamp_ids: Optional[List[str]] = None,
    ) -> List[Any]:
        """
        Get only the data objects (without metadata) that match the filtering criteria.

        Args:
            battery_ids: List of battery IDs to include (None = all)
            temperatures: List of temperatures to include (None = all)
            battery_modes: List of battery modes to include (None = all)
            mode_phases: List of mode phases to include (None = all)
            timestamp_ids: List of timestamp IDs to include (None = all)

        Returns:
            List of data objects only
        """
        data_list = []

        # Apply filters and collect only data
        for battery_id in self._data:
            if battery_ids and battery_id not in battery_ids:
                continue

            for temperature in self._data[battery_id]:
                if temperatures and temperature not in temperatures:
                    continue

                for battery_mode in self._data[battery_id][temperature]:
                    if battery_modes and battery_mode not in battery_modes:
                        continue

                    for mode_phase in self._data[battery_id][temperature][battery_mode]:
                        if mode_phases and mode_phase not in mode_phases:
                            continue

                        for timestamp_id in self._data[battery_id][temperature][
                            battery_mode
                        ][mode_phase]:
                            if timestamp_ids and timestamp_id not in timestamp_ids:
                                continue

                            # Get only the data
                            data = self.get_data(
                                battery_id,
                                temperature,
                                battery_mode,
                                mode_phase,
                                timestamp_id,
                            )
                            if data is not None:
                                data_list.append(data)

        return data_list

    def get_data_for_battery_temp(
        self, battery_id: str, temperature: str
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to get all data for a specific battery and temperature.

        Args:
            battery_id: The battery identifier
            temperature: The temperature value (as string)

        Returns:
            List of data entries for the specified battery and temperature
        """
        return self.get_data_list(battery_ids=[battery_id], temperatures=[temperature])

    def get_data_for_mode_phase(
        self, battery_mode: str, mode_phase: str
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to get all data for a specific mode and phase across all batteries and temperatures.

        Args:
            battery_mode: The battery mode (e.g., 'linear', 'switching')
            mode_phase: The mode phase (e.g., 'charging', 'discharging')

        Returns:
            List of data entries for the specified mode and phase
        """
        return self.get_data_list(
            battery_modes=[battery_mode], mode_phases=[mode_phase]
        )

    def get_charging_data(
        self,
        battery_ids: Optional[List[str]] = None,
        temperatures: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to get all charging data.

        Args:
            battery_ids: Optional list of battery IDs to filter by
            temperatures: Optional list of temperatures to filter by

        Returns:
            List of charging data entries
        """
        return self.get_data_list(
            battery_ids=battery_ids, temperatures=temperatures, mode_phases=["charging"]
        )

    def get_discharging_data(
        self,
        battery_ids: Optional[List[str]] = None,
        temperatures: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to get all discharging data.

        Args:
            battery_ids: Optional list of battery IDs to filter by
            temperatures: Optional list of temperatures to filter by

        Returns:
            List of discharging data entries
        """
        return self.get_data_list(
            battery_ids=battery_ids,
            temperatures=temperatures,
            mode_phases=["discharging"],
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics including dataset hash."""
        stats = self._stats.copy()
        stats.update(
            {
                "unique_battery_ids": len(self.get_battery_ids()),
                "total_profiles": sum(
                    len(self.get_timestamp_ids(bid, temp, bm, mp))
                    for bid in self.get_battery_ids()
                    for temp in self.get_temperatures(bid)
                    for bm in self.get_battery_modes(bid, temp)
                    for mp in self.get_mode_phases(bid, temp, bm)
                ),
                "dataset_hash": self._dataset_hash,
            }
        )
        return stats

    def print_structure(self, max_depth: int = 5):
        """Print the hierarchical structure of the dataset."""
        print("Dataset Structure:")
        print(f"├── Battery IDs: {self.get_battery_ids()}")

        for battery_id in self.get_battery_ids()[
            :2
        ]:  # Show first 2 batteries as example
            temperatures = self.get_temperatures(battery_id)
            print(f"│   ├── {battery_id}/")
            print(f"│   │   ├── Temperatures: {temperatures}")

            if max_depth > 2:
                for temperature in temperatures[
                    :1
                ]:  # Show first temperature as example
                    battery_modes = self.get_battery_modes(battery_id, temperature)
                    print(f"│   │   │   ├── {temperature}°C/")
                    print(f"│   │   │   │   ├── Modes: {battery_modes}")

                    if max_depth > 3:
                        for battery_mode in battery_modes:
                            mode_phases = self.get_mode_phases(
                                battery_id, temperature, battery_mode
                            )
                            print(f"│   │   │   │   │   ├── {battery_mode}/")
                            print(f"│   │   │   │   │   │   ├── Phases: {mode_phases}")

                            if max_depth > 4:
                                for mode_phase in mode_phases:
                                    timestamp_ids = self.get_timestamp_ids(
                                        battery_id,
                                        temperature,
                                        battery_mode,
                                        mode_phase,
                                    )
                                    print(
                                        f"│   │   │   │   │   │   │   ├── {mode_phase}/"
                                    )
                                    print(
                                        f"│   │   │   │   │   │   │   │   └── Timestamps: {timestamp_ids}"
                                    )

        if len(self.get_battery_ids()) > 2:
            print(f"│   └── ... and {len(self.get_battery_ids()) - 2} more batteries")

    def __len__(self) -> int:
        """Return total number of profiles in the dataset."""
        return self.get_statistics()["total_profiles"]

    def __repr__(self) -> str:
        """String representation of the dataset."""
        stats = self.get_statistics()
        return (
            f"BatteryDataset(path='{self.dataset_path}', "
            f"batteries={stats['unique_battery_ids']}, "
            f"profiles={stats['total_profiles']}, "
            f"hash={stats['dataset_hash']})"
        )


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    dataset_path = Path("datasets/ts7_battery_data_JYHPFL333838")

    # Load dataset
    battery_dataset = BatteryDataset(dataset_path)

    # Print statistics
    print(battery_dataset)
    print("\nStatistics:", battery_dataset.get_statistics())

    # Print structure
    battery_dataset.print_structure()

    # Access data
    battery_ids = battery_dataset.get_battery_ids()
    if battery_ids:
        first_battery = battery_ids[0]
        temperatures = battery_dataset.get_temperatures(first_battery)
        if temperatures:
            first_temperature = temperatures[0]
            modes = battery_dataset.get_battery_modes(first_battery, first_temperature)
            print(f"\nModes for {first_battery} at {first_temperature}°C: {modes}")

    # Filter example
    filtered = battery_dataset.filter(
        battery_modes=["linear", "switching"], mode_phases=["charging", "discharging"]
    )
    print(f"\nFiltered dataset: {filtered}")
