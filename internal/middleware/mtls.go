package middleware

import (
	"context"
	"crypto/x509"
	"fmt"
	"net/http"
	"strings"
)

type tenantContextKey string

const (
	tenantIDKey tenantContextKey = "tenant_id"
	sanKey      tenantContextKey = "san"
)

type TenantContext struct {
	TenantID string
	SANs     []string
	Subject  string
}

func TenantFromContext(ctx context.Context) (string, bool) {
	v := ctx.Value(tenantIDKey)
	if v == nil {
		return "", false
	}
	s, ok := v.(string)
	return s, ok && s != ""
}

func SANsFromContext(ctx context.Context) ([]string, bool) {
	v := ctx.Value(sanKey)
	if v == nil {
		return nil, false
	}
	s, ok := v.([]string)
	return s, ok
}

func MTLSMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.TLS == nil || len(r.TLS.PeerCertificates) == 0 {
			http.Error(w, "mutual TLS required", http.StatusUnauthorized)
			return
		}

		cert := r.TLS.PeerCertificates[0]
		tenantID := extractTenant(cert)
		if tenantID == "" {
			http.Error(w, "tenant identity missing in client certificate", http.StatusUnauthorized)
			return
		}

		sans := extractSANs(cert)
		ctx := context.WithValue(r.Context(), tenantIDKey, tenantID)
		ctx = context.WithValue(ctx, sanKey, sans)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func extractTenant(cert *x509.Certificate) string {
	if len(cert.Subject.Organization) > 0 && cert.Subject.Organization[0] != "" {
		return cert.Subject.Organization[0]
	}
	if cert.Subject.CommonName != "" {
		return cert.Subject.CommonName
	}
	if len(cert.URIs) > 0 && cert.URIs[0].String() != "" {
		return cert.URIs[0].String()
	}
	return ""
}

func extractSANs(cert *x509.Certificate) []string {
	out := make([]string, 0, len(cert.DNSNames)+len(cert.EmailAddresses)+len(cert.IPAddresses)+len(cert.URIs))
	for _, name := range cert.DNSNames {
		out = append(out, name)
	}
	for _, email := range cert.EmailAddresses {
		out = append(out, email)
	}
	for _, ip := range cert.IPAddresses {
		out = append(out, ip.String())
	}
	for _, u := range cert.URIs {
		out = append(out, u.String())
	}
	return out
}

func MarshalTenantContext(ctx context.Context) (TenantContext, error) {
	tenantID, ok := TenantFromContext(ctx)
	if !ok {
		return TenantContext{}, fmt.Errorf("tenant not found")
	}
	sans, _ := SANsFromContext(ctx)
	return TenantContext{TenantID: tenantID, SANs: sans}, nil
}

func (t TenantContext) String() string {
	return strings.Join(t.SANs, ",")
}
