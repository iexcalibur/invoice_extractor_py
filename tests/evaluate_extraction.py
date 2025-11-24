#!/usr/bin/env python3

import json
import sqlite3
from typing import Dict, List, Tuple
import pandas as pd
from pathlib import Path

class GroundTruthEvaluator:
    def __init__(self, db_path: str = "invoices.db", gt_file: str = "ground_truth.json"):
        self.db_path = db_path
        self.gt_file = gt_file
        self.conn = None
        
    def load_ground_truth(self) -> Dict:
        if not Path(self.gt_file).exists():
            raise FileNotFoundError(f"Ground truth file not found: {self.gt_file}")
        
        with open(self.gt_file, 'r') as f:
            return json.load(f)
    
    def connect_db(self):
        self.conn = sqlite3.connect(self.db_path)
        
    def close_db(self):
        if self.conn:
            self.conn.close()
    
    def get_invoice_by_number(self, invoice_number: str) -> Dict:
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT id, invoice_number, vendor_name, invoice_date, total_amount, 
                   extraction_method, confidence_score
            FROM invoices 
            WHERE invoice_number = ?
        """, (invoice_number,))
        
        result = cursor.fetchone()
        if not result:
            return None
        
        inv_id, inv_num, vendor, date, total, method, conf = result
        
        cursor.execute("""
            SELECT description, quantity, unit_price, line_total
            FROM line_items
            WHERE invoice_id = ?
        """, (inv_id,))
        
        line_items = cursor.fetchall()
        
        return {
            'id': inv_id,
            'invoice_number': inv_num,
            'vendor_name': vendor,
            'invoice_date': date,
            'total_amount': float(total),
            'extraction_method': method,
            'confidence_score': float(conf or 0.0),
            'line_items': [
                {
                    'description': item[0],
                    'quantity': float(item[1]),
                    'unit_price': float(item[2]),
                    'line_total': float(item[3])
                }
                for item in line_items
            ],
            'line_items_count': len(line_items)
        }
    
    def normalize_value(self, value, field_type: str) -> str:
        if value is None:
            return ""
        
        value_str = str(value).strip().lower()
        
        if field_type == 'date':
            value_str = value_str.replace('/', '-')
        elif field_type == 'amount':
            try:
                value_str = f"{float(value_str):.2f}"
            except:
                pass
        
        return value_str
    
    def compare_field(self, extracted, ground_truth, field_type: str = 'text') -> bool:
        extracted_norm = self.normalize_value(extracted, field_type)
        gt_norm = self.normalize_value(ground_truth, field_type)
        return extracted_norm == gt_norm
    
    def evaluate(self) -> Dict:
        gt_data = self.load_ground_truth()
        
        self.connect_db()
        
        fields = {
            'invoice_number': 'text',
            'vendor_name': 'text',
            'invoice_date': 'date',
            'total_amount': 'amount',
            'line_items_count': 'text'
        }
        
        results = {
            'field_metrics': {},
            'overall_metrics': {},
            'detailed_errors': [],
            'summary': {
                'total_invoices': 0,
                'evaluated_invoices': 0,
                'missing_invoices': []
            }
        }
        
        # Collect ground truth invoices
        gt_invoices = []
        for key, value in gt_data.items():
            if key.startswith('page_'):
                gt_invoices.append(value)
        
        results['summary']['total_invoices'] = len(gt_invoices)
        
        print("="*80)
        print("EVALUATING EXTRACTION ACCURACY")
        print("="*80)
        print(f"\nGround Truth File: {self.gt_file}")
        print(f"Total Invoices to Evaluate: {len(gt_invoices)}\n")
        
        for field, field_type in fields.items():
            tp = 0
            fp = 0
            fn = 0
            errors = []
            
            for gt_invoice in gt_invoices:
                inv_num = gt_invoice['invoice_number']
                
                extracted_invoice = self.get_invoice_by_number(inv_num)
                
                if not extracted_invoice:
                    fn += 1
                    results['summary']['missing_invoices'].append(inv_num)
                    errors.append({
                        'invoice_number': inv_num,
                        'field': field,
                        'error': 'Invoice not found in database',
                        'ground_truth': gt_invoice.get(field),
                        'extracted': None
                    })
                    continue
                
                gt_value = gt_invoice.get(field)
                extracted_value = extracted_invoice.get(field)
                
                if self.compare_field(extracted_value, gt_value, field_type):
                    tp += 1
                else:
                    fp += 1
                    errors.append({
                        'invoice_number': inv_num,
                        'field': field,
                        'error': 'Value mismatch',
                        'ground_truth': gt_value,
                        'extracted': extracted_value
                    })
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            results['field_metrics'][field] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'tp': tp,
                'fp': fp,
                'fn': fn,
                'accuracy': tp / len(gt_invoices) if len(gt_invoices) > 0 else 0.0,
                'errors': errors
            }
        
        if results['field_metrics']:
            avg_precision = sum(m['precision'] for m in results['field_metrics'].values()) / len(results['field_metrics'])
            avg_recall = sum(m['recall'] for m in results['field_metrics'].values()) / len(results['field_metrics'])
            avg_f1 = sum(m['f1'] for m in results['field_metrics'].values()) / len(results['field_metrics'])
            avg_accuracy = sum(m['accuracy'] for m in results['field_metrics'].values()) / len(results['field_metrics'])
            
            results['overall_metrics'] = {
                'precision': avg_precision,
                'recall': avg_recall,
                'f1': avg_f1,
                'accuracy': avg_accuracy
            }
        
        results['summary']['evaluated_invoices'] = len(gt_invoices) - len(results['summary']['missing_invoices'])
        
        self.close_db()
        
        return results
    
    def display_results(self, results: Dict):
        print("\n" + "="*80)
        print("EVALUATION RESULTS")
        print("="*80)
        
        summary = results['summary']
        print(f"\nSummary:")
        print(f"   Total Invoices in Ground Truth: {summary['total_invoices']}")
        print(f"   Successfully Evaluated: {summary['evaluated_invoices']}")
        if summary['missing_invoices']:
            print(f"   WARNING: Missing in Database: {len(summary['missing_invoices'])} - {summary['missing_invoices']}")
        
        print("\n" + "-"*80)
        print(f"{'Field':<25} {'Precision':<12} {'Recall':<12} {'F1 Score':<12} {'Accuracy':<12}")
        print("-"*80)
        
        for field, metrics in results['field_metrics'].items():
            print(f"{field:<25} {metrics['precision']:>10.2%} {metrics['recall']:>10.2%} "
                  f"{metrics['f1']:>10.2%} {metrics['accuracy']:>10.2%}")
        
        print("-"*80)
        om = results['overall_metrics']
        print(f"{'OVERALL AVERAGE':<25} {om['precision']:>10.2%} {om['recall']:>10.2%} "
              f"{om['f1']:>10.2%} {om['accuracy']:>10.2%}")
        print("="*80)
        
        total_errors = sum(len(m['errors']) for m in results['field_metrics'].values() if m['errors'])
        
        if total_errors > 0:
            print(f"\nWARNING: ERRORS FOUND: {total_errors}")
            print("-"*80)
            
            for field, metrics in results['field_metrics'].items():
                if metrics['errors']:
                    print(f"\nERROR: {field.upper()} - {len(metrics['errors'])} error(s):")
                    for err in metrics['errors'][:5]:
                        print(f"   Invoice #{err['invoice_number']}:")
                        print(f"      Ground Truth: {err['ground_truth']}")
                        print(f"      Extracted:    {err['extracted']}")
                        if err.get('error'):
                            print(f"      Issue:        {err['error']}")
                    
                    if len(metrics['errors']) > 5:
                        print(f"   ... and {len(metrics['errors']) - 5} more errors")
        else:
            print("\nNO ERRORS - Perfect extraction!")
        
        print("\n" + "="*80)
    
    def export_results(self, results: Dict, output_file: str = "evaluation_results.json"):
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_file}")


def main():
    evaluator = GroundTruthEvaluator(
        db_path="invoices.db",
        gt_file="ground_truth.json"
    )
    
    try:
        results = evaluator.evaluate()
        
        evaluator.display_results(results)
        
        evaluator.export_results(results)
        
        return results
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease ensure:")
        print("1. ground_truth.json exists in the current directory")
        print("2. invoices.db exists in the current directory")
        return None
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = main()
