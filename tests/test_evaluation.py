#!/usr/bin/env python3
"""
Quick setup and test script for ground truth evaluation

This script:
1. Checks if ground_truth.json exists
2. Runs the evaluation
3. Shows the results
"""

from pathlib import Path
import sys

def check_files():
    """Check if required files exist"""
    print("="*80)
    print("🔍 CHECKING REQUIRED FILES")
    print("="*80)
    
    project_root = Path(__file__).parent.parent
    files = {
        'tests/ground_truth.json': 'Ground truth data',
        'invoices.db': 'Invoice database',
        'tests/evaluate_extraction.py': 'Evaluation script'
    }
    
    all_exist = True
    for file, description in files.items():
        path = project_root / file
        if path.exists():
            print(f"✅ {file:<30} - {description}")
        else:
            print(f"❌ {file:<30} - {description} (NOT FOUND)")
            all_exist = False
    
    print("="*80)
    return all_exist

def run_evaluation():
    """Run the evaluation"""
    from evaluate_extraction import GroundTruthEvaluator
    
    # Get paths relative to project root
    project_root = Path(__file__).parent.parent
    evaluator = GroundTruthEvaluator(
        db_path=str(project_root / "invoices.db"),
        gt_file=str(project_root / "tests" / "ground_truth.json")
    )
    
    # Run evaluation
    results = evaluator.evaluate()
    
    # Display results
    evaluator.display_results(results)
    
    # Export results
    evaluator.export_results(results)
    
    return results

def main():
    print("\n🚀 GROUND TRUTH EVALUATION - QUICK TEST\n")
    
    # Check files
    if not check_files():
        print("\n⚠️  Missing required files!")
        print("\nSetup instructions:")
        print("1. Ensure ground_truth.json is in the current directory")
        print("2. Ensure invoices.db is in the current directory")
        print("3. Run this script again")
        sys.exit(1)
    
    print("\n✅ All files found! Running evaluation...\n")
    
    # Run evaluation
    try:
        results = run_evaluation()
        
        if results:
            print("\n✅ Evaluation completed successfully!")
            print(f"\n🎯 Quick Summary:")
            print(f"   Overall F1 Score: {results['overall_metrics']['f1']:.2%}")
            print(f"   Overall Accuracy: {results['overall_metrics']['accuracy']:.2%}")
            print(f"   Invoices Evaluated: {results['summary']['evaluated_invoices']}/{results['summary']['total_invoices']}")
            
    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
