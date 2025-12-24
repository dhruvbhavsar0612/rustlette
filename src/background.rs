//! Background task management for Rustlette
//!
//! This module implements background task execution that allows tasks to be
//! queued and executed asynchronously after the response is sent to the client.

use crate::error::{RustletteError, RustletteResult};
use pyo3::prelude::*;
use std::collections::VecDeque;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{mpsc, Mutex};
use tokio::task::JoinHandle;

/// A background task that can be executed asynchronously
#[derive(Debug, Clone)]
#[pyclass]
pub struct BackgroundTask {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub name: String,

    // Internal fields
    func: PyObject,
    args: Vec<PyObject>,
    kwargs: Option<PyObject>,
    delay: Option<Duration>,
    max_retries: u32,
    current_retry: u32,
}

#[pymethods]
impl BackgroundTask {
    #[new]
    #[pyo3(signature = (func, args=None, kwargs=None, name=None, delay=None, max_retries=0))]
    pub fn new(
        func: PyObject,
        args: Option<Vec<PyObject>>,
        kwargs: Option<PyObject>,
        name: Option<String>,
        delay: Option<f64>,
        max_retries: Option<u32>,
    ) -> PyResult<Self> {
        let id = uuid::Uuid::new_v4().to_string();
        let name = name.unwrap_or_else(|| {
            Python::with_gil(|py| {
                func.getattr(py, "__name__")
                    .and_then(|n| n.extract::<String>(py))
                    .unwrap_or_else(|_| "BackgroundTask".to_string())
            })
        });

        let delay = delay.map(|d| Duration::from_secs_f64(d));

        Ok(Self {
            id,
            name,
            func,
            args: args.unwrap_or_default(),
            kwargs,
            delay,
            max_retries: max_retries.unwrap_or(0),
            current_retry: 0,
        })
    }

    /// Execute the background task
    pub fn execute(&mut self) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let args = if self.args.is_empty() {
                pyo3::types::PyTuple::empty(py)
            } else {
                pyo3::types::PyTuple::new(py, &self.args)
            };

            let result = if let Some(ref kwargs) = self.kwargs {
                if let Ok(kwargs_dict) = kwargs.downcast::<pyo3::types::PyDict>(py) {
                    self.func.call(py, args, Some(kwargs_dict))
                } else {
                    self.func.call1(py, args)
                }
            } else {
                self.func.call1(py, args)
            };

            match result {
                Ok(result) => Ok(result),
                Err(e) => {
                    self.current_retry += 1;
                    if self.current_retry <= self.max_retries {
                        tracing::warn!(
                            "Background task '{}' failed (attempt {}/{}): {}",
                            self.name,
                            self.current_retry,
                            self.max_retries + 1,
                            e
                        );
                        Err(e)
                    } else {
                        tracing::error!(
                            "Background task '{}' failed after {} attempts: {}",
                            self.name,
                            self.max_retries + 1,
                            e
                        );
                        Err(e)
                    }
                }
            }
        })
    }

    /// Check if the task should be retried
    #[getter]
    pub fn should_retry(&self) -> bool {
        self.current_retry <= self.max_retries
    }

    /// Get the delay before execution
    #[getter]
    pub fn delay_seconds(&self) -> Option<f64> {
        self.delay.map(|d| d.as_secs_f64())
    }

    /// Get current retry count
    #[getter]
    pub fn retry_count(&self) -> u32 {
        self.current_retry
    }

    fn __repr__(&self) -> String {
        format!(
            "BackgroundTask(id='{}', name='{}', retries={}/{})",
            self.id, self.name, self.current_retry, self.max_retries
        )
    }
}

impl BackgroundTask {
    /// Create a simple background task
    pub fn simple(func: PyObject, args: Vec<PyObject>) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            name: Python::with_gil(|py| {
                func.getattr(py, "__name__")
                    .and_then(|n| n.extract::<String>(py))
                    .unwrap_or_else(|_| "BackgroundTask".to_string())
            }),
            func,
            args,
            kwargs: None,
            delay: None,
            max_retries: 0,
            current_retry: 0,
        }
    }

    /// Get the delay duration
    pub fn delay_duration(&self) -> Option<Duration> {
        self.delay
    }
}

/// Background task execution result
#[derive(Debug)]
pub enum TaskResult {
    Success(PyObject),
    Failure(PyErr),
    Retry(BackgroundTask),
}

/// Background task queue for managing task execution
#[derive(Debug)]
pub struct TaskQueue {
    tasks: Arc<Mutex<VecDeque<BackgroundTask>>>,
    sender: mpsc::UnboundedSender<BackgroundTask>,
    receiver: Arc<Mutex<mpsc::UnboundedReceiver<BackgroundTask>>>,
    workers: Vec<JoinHandle<()>>,
    is_running: Arc<Mutex<bool>>,
}

impl TaskQueue {
    /// Create a new task queue with the specified number of workers
    pub fn new(num_workers: usize) -> Self {
        let (sender, receiver) = mpsc::unbounded_channel();
        let tasks = Arc::new(Mutex::new(VecDeque::new()));
        let is_running = Arc::new(Mutex::new(false));

        Self {
            tasks,
            sender,
            receiver: Arc::new(Mutex::new(receiver)),
            workers: Vec::with_capacity(num_workers),
            is_running,
        }
    }

    /// Start the task queue workers
    pub async fn start(&mut self) -> RustletteResult<()> {
        let mut is_running = self.is_running.lock().await;
        if *is_running {
            return Ok(()); // Already running
        }

        *is_running = true;
        drop(is_running);

        let num_workers = self.workers.capacity();
        for worker_id in 0..num_workers {
            let receiver = self.receiver.clone();
            let is_running = self.is_running.clone();

            let worker = tokio::spawn(async move {
                Self::worker_loop(worker_id, receiver, is_running).await;
            });

            self.workers.push(worker);
        }

        tracing::info!("Started {} background task workers", num_workers);
        Ok(())
    }

    /// Stop the task queue workers
    pub async fn stop(&mut self) -> RustletteResult<()> {
        let mut is_running = self.is_running.lock().await;
        *is_running = false;
        drop(is_running);

        // Wait for all workers to finish
        for worker in self.workers.drain(..) {
            if let Err(e) = worker.await {
                tracing::error!("Error stopping background task worker: {}", e);
            }
        }

        tracing::info!("Stopped all background task workers");
        Ok(())
    }

    /// Add a task to the queue
    pub async fn enqueue(&self, task: BackgroundTask) -> RustletteResult<()> {
        if let Some(delay) = task.delay_duration() {
            // Schedule delayed task
            let sender = self.sender.clone();
            tokio::spawn(async move {
                tokio::time::sleep(delay).await;
                if let Err(e) = sender.send(task) {
                    tracing::error!("Failed to send delayed task: {}", e);
                }
            });
        } else {
            // Send immediately
            self.sender.send(task).map_err(|e| {
                RustletteError::internal_error(format!("Failed to enqueue task: {}", e))
            })?;
        }

        Ok(())
    }

    /// Get the number of pending tasks
    pub async fn pending_count(&self) -> usize {
        self.tasks.lock().await.len()
    }

    /// Check if the queue is running
    pub async fn is_running(&self) -> bool {
        *self.is_running.lock().await
    }

    /// Worker loop for processing background tasks
    async fn worker_loop(
        worker_id: usize,
        receiver: Arc<Mutex<mpsc::UnboundedReceiver<BackgroundTask>>>,
        is_running: Arc<Mutex<bool>>,
    ) {
        tracing::debug!("Background task worker {} started", worker_id);

        loop {
            // Check if we should stop
            {
                let running = is_running.lock().await;
                if !*running {
                    break;
                }
            }

            // Try to receive a task
            let task = {
                let mut receiver = receiver.lock().await;
                receiver.recv().await
            };

            match task {
                Some(mut task) => {
                    tracing::debug!("Worker {} executing task '{}'", worker_id, task.name);

                    let start_time = std::time::Instant::now();
                    match task.execute() {
                        Ok(_) => {
                            let duration = start_time.elapsed();
                            tracing::info!(
                                "Background task '{}' completed successfully in {:?}",
                                task.name,
                                duration
                            );
                        }
                        Err(e) => {
                            let duration = start_time.elapsed();
                            if task.should_retry() {
                                tracing::warn!(
                                    "Background task '{}' failed after {:?}, will retry: {}",
                                    task.name,
                                    duration,
                                    e
                                );
                                // TODO: Re-enqueue the task for retry
                            } else {
                                tracing::error!(
                                    "Background task '{}' failed permanently after {:?}: {}",
                                    task.name,
                                    duration,
                                    e
                                );
                            }
                        }
                    }
                }
                None => {
                    // Channel closed, stop the worker
                    break;
                }
            }
        }

        tracing::debug!("Background task worker {} stopped", worker_id);
    }
}

/// Global background task manager
#[derive(Debug)]
#[pyclass]
pub struct BackgroundTaskManager {
    queue: Arc<Mutex<Option<TaskQueue>>>,
    num_workers: usize,
}

#[pymethods]
impl BackgroundTaskManager {
    #[new]
    pub fn new(num_workers: Option<usize>) -> Self {
        Self {
            queue: Arc::new(Mutex::new(None)),
            num_workers: num_workers.unwrap_or(4),
        }
    }

    /// Start the background task manager
    pub fn start<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let queue = Arc::clone(&self.queue);
        let num_workers = self.num_workers;

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut queue_guard = queue.lock().await;
            if queue_guard.is_none() {
                let mut task_queue = TaskQueue::new(num_workers);
                task_queue
                    .start()
                    .await
                    .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
                *queue_guard = Some(task_queue);
            }
            Ok(())
        })
    }

    /// Stop the background task manager
    pub fn stop<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let queue = Arc::clone(&self.queue);

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let mut queue_guard = queue.lock().await;
            if let Some(mut task_queue) = queue_guard.take() {
                task_queue
                    .stop()
                    .await
                    .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            }
            Ok(())
        })
    }

    /// Add a background task
    pub fn add_task<'py>(&self, py: Python<'py>, task: BackgroundTask) -> PyResult<&'py PyAny> {
        let queue = Arc::clone(&self.queue);

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let queue_guard = queue.lock().await;
            if let Some(ref task_queue) = *queue_guard {
                task_queue
                    .enqueue(task)
                    .await
                    .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            } else {
                return Err(pyo3::exceptions::PyRuntimeError::new_err(
                    "Background task manager not started",
                ));
            }
            Ok(())
        })
    }

    /// Get the number of pending tasks
    pub fn pending_count<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let queue = Arc::clone(&self.queue);

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let queue_guard = queue.lock().await;
            if let Some(ref task_queue) = *queue_guard {
                Ok(task_queue.pending_count().await)
            } else {
                Ok(0)
            }
        })
    }

    /// Check if the manager is running
    #[getter]
    pub fn is_running<'py>(&self, py: Python<'py>) -> PyResult<&'py PyAny> {
        let queue = Arc::clone(&self.queue);

        pyo3_asyncio::tokio::future_into_py(py, async move {
            let queue_guard = queue.lock().await;
            if let Some(ref task_queue) = *queue_guard {
                Ok(task_queue.is_running().await)
            } else {
                Ok(false)
            }
        })
    }

    /// Get the number of workers
    #[getter]
    pub fn worker_count(&self) -> usize {
        self.num_workers
    }

    fn __repr__(&self) -> String {
        format!("BackgroundTaskManager({} workers)", self.num_workers)
    }
}

impl Default for BackgroundTaskManager {
    fn default() -> Self {
        Self::new(None)
    }
}

impl BackgroundTaskManager {
    /// Create a global instance
    pub fn global() -> &'static Self {
        use once_cell::sync::Lazy;
        static INSTANCE: Lazy<BackgroundTaskManager> =
            Lazy::new(|| BackgroundTaskManager::new(Some(4)));
        &INSTANCE
    }

    /// Add a task to the global manager
    pub async fn add_task_async(&self, task: BackgroundTask) -> RustletteResult<()> {
        let queue_guard = self.queue.lock().await;
        if let Some(ref task_queue) = *queue_guard {
            task_queue.enqueue(task).await
        } else {
            Err(RustletteError::internal_error(
                "Background task manager not started",
            ))
        }
    }
}

/// Helper functions for creating common background tasks
pub mod helpers {
    use super::*;

    /// Create a task to send an email
    pub fn send_email_task(
        to: String,
        subject: String,
        body: String,
        smtp_config: PyObject,
    ) -> BackgroundTask {
        Python::with_gil(|py| {
            let args = vec![
                to.to_object(py),
                subject.to_object(py),
                body.to_object(py),
                smtp_config,
            ];

            // This would be a Python function that handles email sending
            let email_func = py
                .eval(
                    "lambda to, subject, body, config: print(f'Sending email to {to}')",
                    None,
                    None,
                )
                .unwrap()
                .to_object(py);

            BackgroundTask::simple(email_func, args)
        })
    }

    /// Create a task to log something
    pub fn log_task(message: String, level: Option<String>) -> BackgroundTask {
        Python::with_gil(|py| {
            let level = level.unwrap_or_else(|| "info".to_string());
            let args = vec![message.to_object(py), level.to_object(py)];

            let log_func = py
                .eval(
                    "lambda msg, level: print(f'[{level.upper()}] {msg}')",
                    None,
                    None,
                )
                .unwrap()
                .to_object(py);

            BackgroundTask::simple(log_func, args)
        })
    }

    /// Create a task to clean up temporary files
    pub fn cleanup_task(file_paths: Vec<String>) -> BackgroundTask {
        Python::with_gil(|py| {
            let args = vec![file_paths.to_object(py)];

            let cleanup_func = py
                .eval(
                    "lambda paths: [__import__('os').remove(p) for p in paths if __import__('os').path.exists(p)]",
                    None,
                    None,
                )
                .unwrap()
                .to_object(py);

            BackgroundTask::simple(cleanup_func, args)
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_background_task_creation() {
        Python::with_gil(|py| {
            let func = py
                .eval("lambda x: x * 2", None, None)
                .unwrap()
                .to_object(py);
            let args = vec![42i32.to_object(py)];

            let mut task = BackgroundTask::simple(func, args);
            let result = task.execute().unwrap();
            let value: i32 = result.extract(py).unwrap();
            assert_eq!(value, 84);
        });
    }

    #[tokio::test]
    async fn test_task_queue() {
        let mut queue = TaskQueue::new(2);
        queue.start().await.unwrap();

        Python::with_gil(|py| {
            let func = py
                .eval("lambda: print('Hello from background task')", None, None)
                .unwrap()
                .to_object(py);

            let task = BackgroundTask::simple(func, vec![]);
            tokio::spawn(async move {
                queue.enqueue(task).await.unwrap();
            });
        });

        // Give some time for the task to execute
        tokio::time::sleep(Duration::from_millis(100)).await;

        queue.stop().await.unwrap();
    }

    #[test]
    fn test_background_task_manager() {
        Python::with_gil(|py| {
            let manager = BackgroundTaskManager::new(Some(2));

            let func = py
                .eval("lambda: print('Test task')", None, None)
                .unwrap()
                .to_object(py);

            let task = BackgroundTask::simple(func, vec![]);

            // Test that we can create the manager and task
            assert_eq!(manager.worker_count(), 2);
            assert_eq!(task.retry_count(), 0);
        });
    }

    #[test]
    fn test_helper_functions() {
        let email_task = helpers::send_email_task(
            "test@example.com".to_string(),
            "Test Subject".to_string(),
            "Test Body".to_string(),
            Python::with_gil(|py| py.None()),
        );

        assert_eq!(email_task.retry_count(), 0);
        assert!(!email_task.name.is_empty());

        let log_task = helpers::log_task("Test message".to_string(), None);
        assert_eq!(log_task.retry_count(), 0);

        let cleanup_task = helpers::cleanup_task(vec!["/tmp/test.txt".to_string()]);
        assert_eq!(cleanup_task.retry_count(), 0);
    }
}
