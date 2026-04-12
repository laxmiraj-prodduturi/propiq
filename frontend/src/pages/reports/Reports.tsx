import { useEffect, useState } from 'react';
import { getPayments } from '../../api/payments';
import { getMaintenanceRequests } from '../../api/maintenance';
import { getProperties } from '../../api/properties';
import { MOCK_MAINTENANCE, MOCK_PAYMENTS, MOCK_PROPERTIES } from '../../data/mockData';
import type { MaintenanceRequest, Payment, Property } from '../../types';

export default function Reports() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [maintenance, setMaintenance] = useState<MaintenanceRequest[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);

  useEffect(() => {
    getPayments().then(setPayments).catch(() => setPayments(MOCK_PAYMENTS));
    getMaintenanceRequests().then(setMaintenance).catch(() => setMaintenance(MOCK_MAINTENANCE));
    getProperties().then(setProperties).catch(() => setProperties(MOCK_PROPERTIES));
  }, []);

  const totalHomes = properties.length;
  const occupiedHomes = properties.filter(property => property.status === 'occupied').length;
  const collectionRate = payments.length ? Math.round((payments.filter(payment => payment.status === 'paid').length / payments.length) * 100) : 0;
  const openMaintenance = maintenance.filter(item => !['resolved', 'closed'].includes(item.status)).length;

  return (
    <div className="animate-in">
      <div className="page-header">
        <div>
          <h2>Reports</h2>
          <p>Operational and financial summary for the current portfolio</p>
        </div>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Collection Rate</div>
          <div className="kpi-value">{collectionRate}%</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Occupancy</div>
          <div className="kpi-value">{occupiedHomes}/{totalHomes || 0}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Open Maintenance</div>
          <div className="kpi-value">{openMaintenance}</div>
        </div>
      </div>

      <div className="card">
        <div className="section-title" style={{ marginBottom: 12 }}>Summary</div>
        <p style={{ color: 'var(--text-secondary)' }}>
          Rent collection is at {collectionRate}%. {openMaintenance} maintenance requests remain open across {properties.length} properties.
          Occupancy currently stands at {totalHomes ? Math.round((occupiedHomes / totalHomes) * 100) : 0}%.
        </p>
      </div>
    </div>
  );
}
