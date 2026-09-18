package main

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"CivicOs/internal/middleware"
)

const (
	defaultAddr        = ":8443"
	defaultRingCap     = 65536
	defaultMaxBodySize = 1 << 20
)

type AuditEvent struct {
	TenantID [24]byte
	Source   [24]byte
	Sequence uint64
	TS       int64
	Payload  [128]byte
	PayloadN int
}

var auditEventPool = sync.Pool{
	New: func() any {
		return &AuditEvent{}
	},
}

type ringBuffer struct {
	slots []*AuditEvent
	head  atomic.Uint64
	tail  atomic.Uint64
	mask  uint64
}

func newRingBuffer(capacity int) *ringBuffer {
	n := 1
	for n < capacity {
		n <<= 1
	}
	return &ringBuffer{
		slots: make([]*AuditEvent, n),
		mask:  uint64(n - 1),
	}
}

func (r *ringBuffer) publish(e *AuditEvent) bool {
	for {
		head := r.head.Load()
		tail := r.tail.Load()
		if head-tail >= uint64(len(r.slots)) {
			return false
		}
		if r.head.CompareAndSwap(head, head+1) {
			r.slots[head&r.mask] = e
			return true
		}
	}
}

func (r *ringBuffer) drain(max int) []*AuditEvent {
	head := r.head.Load()
	tail := r.tail.Load()
	if tail >= head {
		return nil
	}
	out := make([]*AuditEvent, 0, min(max, int(head-tail)))
	for i := tail; i < head && len(out) < max; i++ {
		if e := r.slots[i&r.mask]; e != nil {
			out = append(out, e)
			r.slots[i&r.mask] = nil
		}
	}
	r.tail.Store(head)
	return out
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

type ingestRequest struct {
	TenantID string          `json:"tenant_id"`
	Sequence uint64          `json:"sequence"`
	Source   string          `json:"source"`
	TS       time.Time       `json:"timestamp"`
	Payload  json.RawMessage `json:"payload"`
}

type batchWriter struct {
	out io.Writer
}

func newBatchWriter(out io.Writer) *batchWriter {
	return &batchWriter{out: out}
}

func (w *batchWriter) writeBatch(events []*AuditEvent) error {
	for _, e := range events {
		if _, err := fmt.Fprintf(w.out, "{\"tenant_id\":\"%s\",\"sequence\":%d,\"timestamp\":%d,\"source\":\"%s\",\"payload\":\"%s\"}\n",
			string(bytesWithoutZero(e.TenantID[:])),
			e.Sequence,
			e.TS,
			string(bytesWithoutZero(e.Source[:])),
			base64.StdEncoding.EncodeToString(e.Payload[:e.PayloadN]),
		); err != nil {
			return err
		}
	}
	return nil
}

func bytesWithoutZero(b []byte) []byte {
	end := len(b)
	for end > 0 && b[end-1] == 0 {
		end--
	}
	return b[:end]
}

func loadServerTLS() (*tls.Config, error) {
	certPath := getenv("MTLS_CERT_FILE", "/etc/civic-audit-core/tls/server.crt")
	keyPath := getenv("MTLS_KEY_FILE", "/etc/civic-audit-core/tls/server.key")
	caPath := getenv("MTLS_CLIENT_CA_FILE", "/etc/civic-audit-core/tls/ca.crt")

	cert, err := tls.LoadX509KeyPair(certPath, keyPath)
	if err != nil {
		return nil, err
	}
	caPEM, err := os.ReadFile(caPath)
	if err != nil {
		return nil, err
	}
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(caPEM) {
		return nil, fmt.Errorf("failed to append client CA certs from %s", caPath)
	}
	return &tls.Config{
		MinVersion:   tls.VersionTLS13,
		Certificates: []tls.Certificate{cert},
		ClientCAs:    pool,
		ClientAuth:   tls.RequireAndVerifyClientCert,
	}, nil
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func parseInt(name string, fallback int) int {
	v := os.Getenv(name)
	if v == "" {
		return fallback
	}
	n, err := strconv.Atoi(v)
	if err != nil || n <= 0 {
		return fallback
	}
	return n
}

func decodeEvent(raw []byte) (*AuditEvent, error) {
	var req ingestRequest
	if err := json.Unmarshal(raw, &req); err != nil {
		return nil, err
	}
	evt := auditEventPool.Get().(*AuditEvent)
	*evt = AuditEvent{}
	copy(evt.TenantID[:], req.TenantID)
	copy(evt.Source[:], req.Source)
	evt.Sequence = req.Sequence
	evt.TS = req.TS.UnixNano()
	if len(req.Payload) > 0 {
		n := copy(evt.Payload[:], req.Payload)
		evt.PayloadN = n
	}
	return evt, nil
}

func releaseEvent(evt *AuditEvent) {
	if evt == nil {
		return
	}
	*evt = AuditEvent{}
	auditEventPool.Put(evt)
}

func (r *ringBuffer) startBatcher(ctx context.Context, w *batchWriter, flushInterval time.Duration, batchSize int) {
	ticker := time.NewTicker(flushInterval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			for {
				evts := r.drain(batchSize)
				if len(evts) == 0 {
					return
				}
				if err := w.writeBatch(evts); err != nil {
					log.Printf("audit writer: %v", err)
				}
				for _, evt := range evts {
					releaseEvent(evt)
				}
			}
		case <-ticker.C:
			evts := r.drain(batchSize)
			if len(evts) == 0 {
				continue
			}
			if err := w.writeBatch(evts); err != nil {
				log.Printf("audit writer: %v", err)
			}
			for _, evt := range evts {
				releaseEvent(evt)
			}
		}
	}
}

func httpHandler(r *ringBuffer) http.HandlerFunc {
	return func(w http.ResponseWriter, req *http.Request) {
		if req.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		if req.ContentLength > int64(defaultMaxBodySize) {
			http.Error(w, "payload too large", http.StatusRequestEntityTooLarge)
			return
		}

		tenant, ok := middleware.TenantFromContext(req.Context())
		if !ok {
			http.Error(w, "tenant not present", http.StatusUnauthorized)
			return
		}

		body, err := io.ReadAll(io.LimitReader(req.Body, defaultMaxBodySize))
		if err != nil {
			http.Error(w, "failed to read body", http.StatusBadRequest)
			return
		}

		evt, err := decodeEvent(body)
		if err != nil {
			http.Error(w, "invalid ingest payload", http.StatusBadRequest)
			return
		}

		if tenant != "" {
			copy(evt.TenantID[:], tenant)
		}

		if !r.publish(evt) {
			releaseEvent(evt)
			http.Error(w, "audit ring full", http.StatusServiceUnavailable)
			return
		}

		w.WriteHeader(http.StatusAccepted)
	}
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	ring := newRingBuffer(parseInt("AUDIT_RING_CAPACITY", defaultRingCap))
	logger := log.New(os.Stdout, "audit-ingest ", log.LstdFlags|log.LUTC)

	writer := newBatchWriter(os.Stdout)
	batcherCtx, cancel := context.WithCancel(ctx)
	defer cancel()
	go ring.startBatcher(batcherCtx, writer, 10*time.Millisecond, 256)

	mux := http.NewServeMux()
	mux.Handle("/v1/audit-events", middleware.MTLSMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		httpHandler(ring)(w, r)
	})))
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	tlsCfg, err := loadServerTLS()
	if err != nil {
		logger.Fatalf("load server tls: %v", err)
	}

	srv := &http.Server{
		Addr:              getenv("AUDIT_ADDR", defaultAddr),
		Handler:           mux,
		TLSConfig:         tlsCfg,
		ReadHeaderTimeout: 2 * time.Second,
		ReadTimeout:       5 * time.Second,
		WriteTimeout:      5 * time.Second,
		IdleTimeout:       30 * time.Second,
	}

	logger.Printf("listening on %s", srv.Addr)
	if err := srv.ListenAndServeTLS("", ""); err != nil && !errors.Is(err, http.ErrServerClosed) {
		logger.Fatalf("serve: %v", err)
	}
}
