import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    const reportPath = path.join(process.cwd(), '..', 'eval', 'latest_eval_report.json');
    if (!fs.existsSync(reportPath)) {
      return NextResponse.json(
        { error: 'Evaluation report snapshot not found on disk.' },
        { status: 404 }
      );
    }

    const fileData = fs.readFileSync(reportPath, 'utf-8');
    const jsonContent = JSON.parse(fileData);
    return NextResponse.json(jsonContent);
  } catch (error: unknown) {
    const errMessage = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { error: `Failed to read eval report from disk: ${errMessage}` },
      { status: 500 }
    );
  }
}
