package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	corev1 "k8s.io/api/core/v1"
	appsv1 "k8s.io/api/apps/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

type ClusterSignal struct {
	Kind      string            `json:"kind"`
	Namespace string            `json:"namespace,omitempty"`
	Name      string            `json:"name,omitempty"`
	Metric    string            `json:"metric"`
	Value     *float64          `json:"value,omitempty"`
	Metadata  map[string]string `json:"metadata,omitempty"`
	Timestamp string            `json:"timestamp"`
}

type SignalBatch struct {
	Signals []ClusterSignal `json:"signals"`
}

var (
	backendURL = getEnv("BACKEND_URL", "http://backend:8000")
	apiToken   = getEnv("API_TOKEN", "")
)

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getKubernetesClient() (*kubernetes.Clientset, error) {
	config, err := rest.InClusterConfig()
	if err != nil {
		// Fallback to kubeconfig for local dev
		kubeconfig := os.Getenv("KUBECONFIG")
		if kubeconfig == "" {
			kubeconfig = os.Getenv("HOME") + "/.kube/config"
		}
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			return nil, err
		}
	}
	return kubernetes.NewForConfig(config)
}

func collectDeploymentSignals(clientset *kubernetes.Clientset) []ClusterSignal {
	var signals []ClusterSignal
	now := time.Now().UTC().Format(time.RFC3339)

	deployments, err := clientset.AppsV1().Deployments("").List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		log.Printf("Error listing deployments: %v", err)
		return signals
	}

	for _, deploy := range deployments.Items {
		replicas := float64(*deploy.Spec.Replicas)
		available := float64(deploy.Status.AvailableReplicas)

		signals = append(signals, ClusterSignal{
			Kind:      "deployment",
			Namespace: deploy.Namespace,
			Name:      deploy.Name,
			Metric:    "replica_count",
			Value:     &replicas,
			Metadata: map[string]string{
				"available_replicas": fmt.Sprintf("%d", deploy.Status.AvailableReplicas),
				"ready_replicas":     fmt.Sprintf("%d", deploy.Status.ReadyReplicas),
			},
			Timestamp: now,
		})

		if replicas > 0 {
			availability := (available / replicas) * 100
			signals = append(signals, ClusterSignal{
				Kind:      "deployment",
				Namespace: deploy.Namespace,
				Name:      deploy.Name,
				Metric:    "availability",
				Value:     &availability,
				Timestamp: now,
			})
		}
	}

	return signals
}

func collectPodSignals(clientset *kubernetes.Clientset) []ClusterSignal {
	var signals []ClusterSignal
	now := time.Now().UTC().Format(time.RFC3339)

	pods, err := clientset.CoreV1().Pods("").List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		log.Printf("Error listing pods: %v", err)
		return signals
	}

	restartCounts := make(map[string]int)

	for _, pod := range pods.Items {
		key := fmt.Sprintf("%s/%s", pod.Namespace, pod.Name)
		maxRestarts := 0

		for _, containerStatus := range pod.Status.ContainerStatuses {
			restarts := int(containerStatus.RestartCount)
			if restarts > maxRestarts {
				maxRestarts = restarts
			}
		}

		restartCounts[key] = maxRestarts

		if maxRestarts > 0 {
			restarts := float64(maxRestarts)
			signals = append(signals, ClusterSignal{
				Kind:      "pod",
				Namespace: pod.Namespace,
				Name:      pod.Name,
				Metric:    "restart_count",
				Value:     &restarts,
				Timestamp: now,
			})
		}
	}

	return signals
}

func collectNodeSignals(clientset *kubernetes.Clientset) []ClusterSignal {
	var signals []ClusterSignal
	now := time.Now().UTC().Format(time.RFC3339)

	nodes, err := clientset.CoreV1().Nodes().List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		log.Printf("Error listing nodes: %v", err)
		return signals
	}

	for _, node := range nodes.Items {
		// Check node conditions
		for _, condition := range node.Status.Conditions {
			if condition.Type == corev1.NodeReady {
				ready := 1.0
				if condition.Status != corev1.ConditionTrue {
					ready = 0.0
				}
				signals = append(signals, ClusterSignal{
					Kind:      "node",
					Namespace: "",
					Name:      node.Name,
					Metric:    "ready",
					Value:     &ready,
					Timestamp: now,
				})
			}
		}
	}

	return signals
}

func collectRecentEvents(clientset *kubernetes.Clientset) []ClusterSignal {
	var signals []ClusterSignal
	now := time.Now().UTC().Format(time.RFC3339)
	cutoff := time.Now().Add(-1 * time.Hour)

	events, err := clientset.CoreV1().Events("").List(context.TODO(), metav1.ListOptions{})
	if err != nil {
		log.Printf("Error listing events: %v", err)
		return signals
	}

	for _, event := range events.Items {
		if event.LastTimestamp.Time.Before(cutoff) {
			continue
		}

		// Only collect warning events
		if event.Type == "Warning" {
			value := 1.0
			signals = append(signals, ClusterSignal{
				Kind:      "event",
				Namespace: event.Namespace,
				Name:      event.Name,
				Metric:    "warning_event",
				Value:     &value,
				Metadata: map[string]string{
					"reason":  event.Reason,
					"message": event.Message,
				},
				Timestamp: now,
			})
		}
	}

	return signals
}

func sendSignalsToBackend(signals []ClusterSignal) error {
	if len(signals) == 0 {
		return nil
	}

	batch := SignalBatch{Signals: signals}
	jsonData, err := json.Marshal(batch.Signals)
	if err != nil {
		return fmt.Errorf("error marshaling signals: %v", err)
	}

	url := fmt.Sprintf("%s/api/v1/cluster-signals", backendURL)
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("error creating request: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")
	if apiToken != "" {
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", apiToken))
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("error sending request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("backend returned status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

func watchEvents(clientset *kubernetes.Clientset) {
	watcher, err := clientset.CoreV1().Events("").Watch(context.TODO(), metav1.ListOptions{})
	if err != nil {
		log.Printf("Error creating event watcher: %v", err)
		return
	}
	defer watcher.Stop()

	log.Println("Watching Kubernetes events...")

	for event := range watcher.ResultChan() {
		if event.Type == watch.Error {
			log.Printf("Watch error: %v", event.Object)
			continue
		}

		k8sEvent, ok := event.Object.(*corev1.Event)
		if !ok {
			continue
		}

		if k8sEvent.Type == "Warning" {
			now := time.Now().UTC().Format(time.RFC3339)
			value := 1.0
			signal := ClusterSignal{
				Kind:      "event",
				Namespace: k8sEvent.Namespace,
				Name:      k8sEvent.Name,
				Metric:    "warning_event",
				Value:     &value,
				Metadata: map[string]string{
					"reason":  k8sEvent.Reason,
					"message": k8sEvent.Message,
				},
				Timestamp: now,
			}

			if err := sendSignalsToBackend([]ClusterSignal{signal}); err != nil {
				log.Printf("Error sending event signal: %v", err)
			}
		}
	}
}

func main() {
	log.Println("Starting PatchPulse agent...")

	clientset, err := getKubernetesClient()
	if err != nil {
		log.Fatalf("Error creating Kubernetes client: %v", err)
	}

	// Start event watcher in goroutine
	go watchEvents(clientset)

	// Periodic snapshot collection
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	// Batch sender ticker
	batchTicker := time.NewTicker(30 * time.Second)
	defer batchTicker.Stop()

	var signalBuffer []ClusterSignal

	// Initial collection
	log.Println("Performing initial cluster snapshot...")
	signals := collectDeploymentSignals(clientset)
	signalBuffer = append(signalBuffer, signals...)
	signals = collectPodSignals(clientset)
	signalBuffer = append(signalBuffer, signals...)
	signals = collectNodeSignals(clientset)
	signalBuffer = append(signalBuffer, signals...)
	signals = collectRecentEvents(clientset)
	signalBuffer = append(signalBuffer, signals...)

	for {
		select {
		case <-ticker.C:
			log.Println("Collecting cluster snapshot...")
			signals := collectDeploymentSignals(clientset)
			signalBuffer = append(signalBuffer, signals...)
			signals = collectPodSignals(clientset)
			signalBuffer = append(signalBuffer, signals...)
			signals = collectNodeSignals(clientset)
			signalBuffer = append(signalBuffer, signals...)
			signals = collectRecentEvents(clientset)
			signalBuffer = append(signalBuffer, signals...)

		case <-batchTicker.C:
			if len(signalBuffer) > 0 {
				log.Printf("Sending %d signals to backend...", len(signalBuffer))
				if err := sendSignalsToBackend(signalBuffer); err != nil {
					log.Printf("Error sending signals: %v", err)
				} else {
					signalBuffer = signalBuffer[:0] // Clear buffer
				}
			}
		}
	}
}

