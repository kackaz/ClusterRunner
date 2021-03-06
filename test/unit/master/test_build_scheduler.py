from queue import Queue
from unittest.mock import Mock

from app.master.build import Build
from app.master.build_scheduler import BuildScheduler
from app.master.build_scheduler_pool import BuildSchedulerPool
from app.master.job_config import JobConfig
from app.master.slave import Slave
from app.master.subjob import Subjob
from test.framework.base_unit_test_case import BaseUnitTestCase


class TestBuildScheduler(BaseUnitTestCase):

    def _get_mock_build(self):
        mock_build = Mock(Build)
        mock_build.is_canceled = True
        config_mock = Mock(JobConfig, **{'max_executors': 20, 'max_executors_per_slave': 10})
        mock_build.project_type.job_config.return_value = config_mock
        # We modify the protected member variable because the build_scheduler class
        # utilizes it directly.
        mock_build._unstarted_subjobs = Queue(maxsize=10)
        return mock_build

    def test_execute_next_subjob_or_free_executor_with_canceled_build_frees_executor(self):
        # Arrange
        mock_build = self._get_mock_build()
        mock_build.is_canceled = True
        mock_slave = Mock(Slave, **{'num_executors': 10, 'id': 1})

        # Act
        scheduler = BuildScheduler(mock_build, Mock(BuildSchedulerPool))
        scheduler.allocate_slave(mock_slave)
        scheduler.execute_next_subjob_or_free_executor(mock_slave)

        # Assert
        mock_slave.free_executor.assert_called_once_with()

    def test_executor_or_free_with_canceled_build_tearsdown_and_unallocates_when_all_free(self):
        # Arrange
        mock_build = self._get_mock_build()
        mock_build.is_canceled = True
        mock_slave = Mock(Slave, **{'num_executors': 10, 'id': 1})
        mock_slave.free_executor.return_value = 0

        # Act
        scheduler = BuildScheduler(mock_build, Mock(BuildSchedulerPool))
        scheduler.allocate_slave(mock_slave)
        scheduler.execute_next_subjob_or_free_executor(mock_slave)

        # Assert
        mock_slave.free_executor.assert_called_once_with()
        mock_slave.teardown.assert_called_once_with()

    def test_execute_next_subjob_or_free_executor_with_no_unstarted_subjobs_frees_executors(self):
        # Arrange
        mock_build = self._get_mock_build()
        mock_build.is_canceled = False
        mock_build._unstarted_subjobs = Queue(maxsize=10)
        mock_slave = Mock(Slave, **{'num_executors': 10, 'id': 1})

        # Act
        scheduler = BuildScheduler(mock_build, Mock(BuildSchedulerPool))
        scheduler.allocate_slave(mock_slave)
        scheduler.execute_next_subjob_or_free_executor(mock_slave)

        # Assert
        mock_slave.free_executor.assert_called_once_with()

    def test_executor_or_free_starts_subjob_and_marks_build_in_progress(self):
        # Arrange
        mock_build = self._get_mock_build()
        mock_build.is_canceled = False
        mock_build._unstarted_subjobs = Queue(maxsize=10)
        mock_subjob = Mock(Subjob)
        mock_build._unstarted_subjobs.put(mock_subjob)
        mock_slave = Mock(Slave, **{'num_executors': 10, 'id': 1})

        # Act
        scheduler = BuildScheduler(mock_build, Mock(BuildSchedulerPool))
        scheduler.allocate_slave(mock_slave)
        scheduler.execute_next_subjob_or_free_executor(mock_slave)

        # Assert
        mock_slave.start_subjob.assert_called_once_with(mock_subjob)
        mock_subjob.mark_in_progress.assert_called_once_with(mock_slave)
