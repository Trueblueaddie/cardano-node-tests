"""Tests for node configuration."""
# pylint: disable=abstract-class-instantiated
import json
import logging
import time
from pathlib import Path

import allure
import pytest
from _pytest.tmpdir import TempPathFactory
from cardano_clusterlib import clusterlib

from cardano_node_tests.cluster_management import cluster_management
from cardano_node_tests.tests import common
from cardano_node_tests.utils import cluster_nodes
from cardano_node_tests.utils import helpers
from cardano_node_tests.utils import locking
from cardano_node_tests.utils import temptools

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def epoch_length_start_cluster(tmp_path_factory: TempPathFactory) -> Path:
    """Update *epochLength* to 1200."""
    shared_tmp = temptools.get_pytest_shared_tmp(tmp_path_factory)

    # need to lock because this same fixture can run on several workers in parallel
    with locking.FileLockIfXdist(f"{shared_tmp}/startup_files_epoch_1200.lock"):
        destdir = shared_tmp / "startup_files_epoch_1200"
        destdir.mkdir(exist_ok=True)

        # return existing script if it is already generated by other worker
        destdir_ls = list(destdir.glob("start-cluster*"))
        if destdir_ls:
            return destdir_ls[0]

        startup_files = cluster_nodes.get_cluster_type().cluster_scripts.copy_scripts_files(
            destdir=destdir
        )
        with open(startup_files.genesis_spec, encoding="utf-8") as fp_in:
            genesis_spec = json.load(fp_in)

        genesis_spec["epochLength"] = 1_500

        with open(startup_files.genesis_spec, "w", encoding="utf-8") as fp_out:
            json.dump(genesis_spec, fp_out)

        return startup_files.start_script


@pytest.fixture(scope="module")
def slot_length_start_cluster(tmp_path_factory: TempPathFactory) -> Path:
    """Update *slotLength* to 0.3."""
    shared_tmp = temptools.get_pytest_shared_tmp(tmp_path_factory)

    # need to lock because this same fixture can run on several workers in parallel
    with locking.FileLockIfXdist(f"{shared_tmp}/startup_files_slot_03.lock"):
        destdir = shared_tmp / "startup_files_slot_03"
        destdir.mkdir(exist_ok=True)

        # return existing script if it is already generated by other worker
        destdir_ls = list(destdir.glob("start-cluster*"))
        if destdir_ls:
            return destdir_ls[0]

        startup_files = cluster_nodes.get_cluster_type().cluster_scripts.copy_scripts_files(
            destdir=destdir
        )
        with open(startup_files.genesis_spec, encoding="utf-8") as fp_in:
            genesis_spec = json.load(fp_in)

        genesis_spec["slotLength"] = 0.3

        with open(startup_files.genesis_spec, "w", encoding="utf-8") as fp_out:
            json.dump(genesis_spec, fp_out)

        return startup_files.start_script


@pytest.fixture
def cluster_epoch_length(
    cluster_manager: cluster_management.ClusterManager, epoch_length_start_cluster: Path
) -> clusterlib.ClusterLib:
    return cluster_manager.get(
        lock_resources=[cluster_management.Resources.CLUSTER],
        cleanup=True,
        start_cmd=str(epoch_length_start_cluster),
    )


@pytest.fixture
def cluster_slot_length(
    cluster_manager: cluster_management.ClusterManager, slot_length_start_cluster: Path
) -> clusterlib.ClusterLib:
    return cluster_manager.get(
        lock_resources=[cluster_management.Resources.CLUSTER],
        cleanup=True,
        start_cmd=str(slot_length_start_cluster),
    )


def check_epoch_length(cluster_obj: clusterlib.ClusterLib) -> None:
    end_sec = 20
    end_sec_padded = end_sec + 20  # padded to make sure tip got updated

    epoch = cluster_obj.wait_for_new_epoch()
    time.sleep(cluster_obj.epoch_length_sec - end_sec)
    assert epoch == cluster_obj.g_query.get_epoch()

    time.sleep(end_sec_padded)
    assert epoch + 1 == cluster_obj.g_query.get_epoch()


@pytest.mark.order(5)
@common.SKIPIF_WRONG_ERA
@pytest.mark.long
class TestBasic:
    """Basic tests for node configuration."""

    @allure.link(helpers.get_vcs_link())
    def test_epoch_length(self, cluster_epoch_length: clusterlib.ClusterLib):
        """Test the *epochLength* configuration."""
        cluster = cluster_epoch_length
        common.get_test_id(cluster)

        assert cluster.slot_length == 0.2
        assert cluster.epoch_length == 1_500
        check_epoch_length(cluster)

    @allure.link(helpers.get_vcs_link())
    def test_slot_length(self, cluster_slot_length: clusterlib.ClusterLib):
        """Test the *slotLength* configuration."""
        cluster = cluster_slot_length
        common.get_test_id(cluster)

        assert cluster.slot_length == 0.3
        assert cluster.epoch_length == 1_000
        check_epoch_length(cluster)
